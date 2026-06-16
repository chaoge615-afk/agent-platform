"""MCP Server 管理器

通过 MCP 协议（SSE 传输）连接 content-analysis-system 的 MCP Server，
提供工具发现和调用能力。

连接架构：
    MCPManager
    ├── bilibili-mcp-server (:9001/sse)
    ├── rag-mcp-server      (:9002/sse)
    └── sql-mcp-server      (:9003/sse)
"""
from contextlib import AsyncExitStack
from typing import Optional

from mcp import ClientSession
from mcp.client.sse import sse_client

from src.config import Config


class MCPManager:
    """MCP Server 管理器

    使用 AsyncExitStack 管理多个 SSE 连接的生命周期。
    支持优雅降级：连接失败不崩溃，调用离线服务返回友好错误。
    """

    def __init__(self):
        self.servers = {
            "bilibili": Config.BILIBILI_MCP_URL,
            "rag": Config.RAG_MCP_URL,
            "sql": Config.SQL_MCP_URL,
        }
        self._sessions: dict[str, ClientSession] = {}
        self._connected: dict[str, bool] = {}
        self._exit_stack: Optional[AsyncExitStack] = None

    async def connect_all(self):
        """连接所有 MCP Server

        逐个连接，失败只标记离线不抛异常，确保服务正常启动。
        """
        self._exit_stack = AsyncExitStack()

        for name, url in self.servers.items():
            try:
                # sse_client 建立 SSE 连接，返回 (read_stream, write_stream)
                read, write = await self._exit_stack.enter_async_context(
                    sse_client(url, timeout=10, sse_read_timeout=300)
                )
                # ClientSession 封装 MCP 协议
                session = await self._exit_stack.enter_async_context(
                    ClientSession(read, write)
                )
                # 执行 MCP 握手
                await session.initialize()

                self._sessions[name] = session
                self._connected[name] = True
                print(f"[MCP] 已连接 {name} ({url})")
            except Exception as e:
                self._connected[name] = False
                print(f"[MCP] 连接 {name} ({url}) 失败: {e}")

    async def list_tools(self, server_name: str) -> list:
        """列出指定 Server 的所有工具

        返回工具列表，每个工具包含 name、description、inputSchema。
        服务离线时返回空列表。
        """
        session = self._sessions.get(server_name)
        if not session or not self._connected.get(server_name):
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
        if not self._connected.get(server_name):
            return {"error": f"MCP Server '{server_name}' 未连接", "isError": True}

        session = self._sessions.get(server_name)
        if not session:
            return {"error": f"MCP Server '{server_name}' 会话不存在", "isError": True}

        try:
            result = await session.call_tool(tool_name, arguments)
            return {
                "content": [c.model_dump() for c in result.content],
                "isError": result.isError,
            }
        except Exception as e:
            print(f"[MCP] call_tool({server_name}, {tool_name}) 失败: {e}")
            return {"error": str(e), "isError": True}

    async def close(self):
        """关闭所有 MCP 连接"""
        if self._exit_stack:
            try:
                await self._exit_stack.aclose()
            except Exception as e:
                print(f"[MCP] 关闭连接时出错: {e}")
            finally:
                self._sessions.clear()
                self._connected.clear()
                self._exit_stack = None


# 全局实例
_manager: Optional[MCPManager] = None


def get_mcp_manager() -> MCPManager:
    """获取 MCP 管理器实例"""
    global _manager
    if _manager is None:
        _manager = MCPManager()
    return _manager
