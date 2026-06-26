"""MCP Server 管理器

通过 MCP 协议（SSE 传输）连接 content-analysis-system 的 MCP Server，
提供工具发现和调用能力。

连接架构：
    MCPManager
    ├── bilibili-mcp-server (:9001/sse)
    ├── rag-mcp-server      (:9002/sse)
    └── sql-mcp-server      (:9003/sse)

K-16 修复：SSE 会话失效后能单请求内自愈重连，且 /health 不再误报 connected=true。
"""
import asyncio
from contextlib import AsyncExitStack
from typing import Optional

from mcp import ClientSession
from mcp.client.sse import sse_client

from src.config import Config


class MCPManager:
    """MCP Server 管理器

    使用每 server 独立的 AsyncExitStack 管理 SSE 连接生命周期，支持：
    - 优雅降级：连接失败不崩溃，调用离线服务返回友好错误。
    - 惰性重连：会话失效时单请求内自愈，不依赖下次请求。
    - 并发安全：每个 server 一把锁串行化重连，避免并发各自建 SSE 会话互相覆盖。
    """

    def __init__(self):
        self.servers = {
            "bilibili": Config.BILIBILI_MCP_URL,
            "rag": Config.RAG_MCP_URL,
            "sql": Config.SQL_MCP_URL,
        }
        self._sessions: dict[str, ClientSession] = {}
        self._connected: dict[str, bool] = {}
        # 每 server 独立 AsyncExitStack：重连时单独 aclose 旧 stack，避免僵尸 SSE 流泄漏。
        self._server_stacks: dict[str, AsyncExitStack] = {}
        # 每 server 一把锁：串行化重连，避免多并发请求各自建立 SSE 会话互相覆盖。
        self._reconnect_locks: dict[str, asyncio.Lock] = {
            name: asyncio.Lock() for name in self.servers
        }

    async def _connect_one(self, name: str) -> bool:
        """连接单个 server（connect_all 与 _reconnect 复用）。成功返回 True。

        重连前先 aclose 该 server 旧 stack，清理可能失效的 SSE 流/ClientSession。
        """
        url = self.servers.get(name)
        if not url:
            return False

        # 关闭旧 stack（若有），清理底层 SSE 流/会话，防僵尸流堆积
        old = self._server_stacks.pop(name, None)
        if old is not None:
            try:
                await old.aclose()
            except Exception as e:
                print(f"[MCP] 关闭 {name} 旧连接时出错: {e}")

        stack = AsyncExitStack()
        try:
            # sse_client 建立 SSE 连接，返回 (read_stream, write_stream)
            read, write = await stack.enter_async_context(
                sse_client(url, timeout=10, sse_read_timeout=300)
            )
            # ClientSession 封装 MCP 协议
            session = await stack.enter_async_context(ClientSession(read, write))
            # 执行 MCP 握手
            await session.initialize()

            self._server_stacks[name] = stack
            self._sessions[name] = session
            self._connected[name] = True
            return True
        except Exception as e:
            self._connected[name] = False
            self._sessions.pop(name, None)  # 用 pop 避免并发下 KeyError
            try:
                await stack.aclose()
            except Exception:
                pass
            print(f"[MCP] 连接 {name} ({url}) 失败: {e}")
            return False

    async def connect_all(self):
        """连接所有 MCP Server

        逐个连接，失败只标记离线不抛异常，确保服务正常启动。
        """
        for name in self.servers:
            ok = await self._connect_one(name)
            if ok:
                print(f"[MCP] 已连接 {name} ({self.servers[name]})")

    async def _reconnect(self, server_name: str) -> bool:
        """单个 server 惰性重连（list_tools/call_tool 失败时触发）。

        带锁 + 双检：持锁后若已被其他并发请求重连成功，直接返回，避免重连风暴。
        """
        if server_name not in self._reconnect_locks:
            return False
        async with self._reconnect_locks[server_name]:
            # 双检：持锁后若已被其他请求重连成功，直接返回 True
            if self._connected.get(server_name) and self._sessions.get(server_name):
                return True
            ok = await self._connect_one(server_name)
            if ok:
                print(f"[MCP] 重连成功 {server_name} ({self.servers[server_name]})")
            return ok

    async def list_tools(self, server_name: str) -> list:
        """列出指定 Server 的所有工具。

        返回工具列表，每个工具包含 name、description、inputSchema。
        会话失效时单请求内自愈重连（K-16 真实故障路径）。
        """
        session = self._sessions.get(server_name)
        if not session or not self._connected.get(server_name):
            # 入口已失效：先重连一次
            if not await self._reconnect(server_name):
                return []
            session = self._sessions.get(server_name)
            if not session:
                return []

        try:
            result = await session.list_tools()
            return [
                {
                    "name": t.name,
                    "description": t.description,
                    "inputSchema": t.inputSchema,
                }
                for t in result.tools
            ]
        except Exception as e:
            print(f"[MCP] list_tools({server_name}) 失败: {e}")
            # 标记失效并清理会话，尝试单请求内自愈（不再等到下一次请求）
            self._connected[server_name] = False
            self._sessions.pop(server_name, None)
            if await self._reconnect(server_name):
                session = self._sessions.get(server_name)
                if session:
                    try:
                        result = await session.list_tools()
                        return [
                            {
                                "name": t.name,
                                "description": t.description,
                                "inputSchema": t.inputSchema,
                            }
                            for t in result.tools
                        ]
                    except Exception as e2:
                        print(f"[MCP] list_tools 重试({server_name}) 仍失败: {e2}")
            return []

    async def call_tool(self, server_name: str, tool_name: str, arguments: dict) -> dict:
        """调用指定 Server 的工具

        Args:
            server_name: MCP Server 名称（bilibili/rag/sql）
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            {"content": [...], "isError": bool}
            离线或异常时返回 {"error": "...", "isError": True}
        """
        # not _connected 或会话缺失时先尝试一次重连（修正 diff_sketch 漏掉的入口）
        if not self._connected.get(server_name):
            if not await self._reconnect(server_name):
                return {"error": f"MCP Server '{server_name}' 未连接", "isError": True}

        session = self._sessions.get(server_name)
        if not session:
            if not await self._reconnect(server_name):
                return {"error": f"MCP Server '{server_name}' 会话不存在", "isError": True}
            session = self._sessions.get(server_name)
            if not session:
                return {"error": f"MCP Server '{server_name}' 会话不存在", "isError": True}

        try:
            # 注意：工具调用可能有副作用，此处不在异常分支重试，避免重复执行。
            # 失败只返回 error，由调用方决定是否重试。
            result = await session.call_tool(tool_name, arguments)
            return {
                "content": [c.model_dump() for c in result.content],
                "isError": result.isError,
            }
        except Exception as e:
            print(f"[MCP] call_tool({server_name}, {tool_name}) 失败: {e}")
            # 会话可能已失效，标记以便下次请求触发重连
            self._connected[server_name] = False
            self._sessions.pop(server_name, None)
            return {"error": str(e), "isError": True}

    async def close(self):
        """关闭所有 MCP 连接"""
        for name, stack in list(self._server_stacks.items()):
            try:
                await stack.aclose()
            except Exception as e:
                print(f"[MCP] 关闭 {name} 连接时出错: {e}")
        self._sessions.clear()
        self._connected.clear()
        self._server_stacks.clear()


# 全局实例
_manager: Optional[MCPManager] = None


def get_mcp_manager() -> MCPManager:
    """获取 MCP 管理器实例"""
    global _manager
    if _manager is None:
        _manager = MCPManager()
    return _manager
