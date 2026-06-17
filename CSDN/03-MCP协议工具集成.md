## 系列文章目录

[Agent 智能路由平台（一）：项目介绍与架构设计](./01-项目介绍与架构设计.md)
[Agent 智能路由平台（二）：LangGraph 工作流引擎](./02-LangGraph工作流引擎.md)
Agent 智能路由平台（三）：MCP 协议工具集成
Agent 智能路由平台（四）：记忆系统与长期反思
Agent 智能路由平台（五）：意图分类与 Prompt 工程
Agent 智能路由平台（六）：安全审计与内容护栏
Agent 智能路由平台（七）：A2A 协议与多智能体协作


### 文章目录

+ [系列文章目录](#_0)
+ [前言](#前言)
+ [一、什么是 MCP 协议](#一什么是-mcp-协议)
    + [1. MCP 解决了什么问题](#1-mcp-解决了什么问题)
    + [2. SSE 传输模式](#2-sse-传输模式)
+ [二、三个 MCP Server 的分工](#二三个-mcp-server-的分工)
    + [1. bilibili-mcp-server：9001](#1-bilibili-mcp-server9001)
    + [2. rag-mcp-server：9002](#2-rag-mcp-server9002)
    + [3. sql-mcp-server：9003](#3-sql-mcp-server9003)
+ [三、MCPManager：统一管理多连接](#三mcpmanager统一管理多连接)
    + [1. 类结构设计](#1-类结构设计)
    + [2. AsyncExitStack 生命周期管理](#2-asyncexitstack-生命周期管理)
+ [四、connect_all()：批量连接与优雅降级](#四connect_all批量连接与优雅降级)
    + [1. 连接流程拆解](#1-连接流程拆解)
    + [2. 失败不崩溃的设计哲学](#2-失败不崩溃的设计哲学)
+ [五、list_tools()：动态工具发现](#五list_tools动态工具发现)
+ [六、call_tool()：工具调用的封装](#六call_tool工具调用的封装)
+ [七、_call_mcp_tool()：智能工具选择](#七_call_mcp_tool智能工具选择)
    + [1. 单工具自动选中](#1-单工具自动选中)
    + [2. 多工具常见名匹配](#2-多工具常见名匹配)
+ [八、_extract_text_from_mcp()：结果提取](#八_extract_text_from_mcp结果提取)
+ [九、全局单例：get_mcp_manager()](#九全局单例get_mcp_manager)
+ [十、完整调用链路图](#十完整调用链路图)
+ [总结](#总结)



## 前言

上篇文章我们拆解了 LangGraph 工作流的节点与边，理解了"问题进来→意图分类→路由分发→结果融合"的整体链路。但有一个关键问题留到了今天：路由分发之后，Agent 到底是怎么调用外部服务的？

答案就是 MCP 协议。Model Context Protocol 是 Anthropic 推出的一套标准化工具调用协议，让 Agent 可以用统一的方式连接各种外部能力——不管背后是数据库查询、语义检索还是视频内容分析，Agent 都不需要关心具体实现，只需要知道"调用哪个工具、传什么参数、拿什么结果"。

这篇文章我会从协议原理讲到工程实现，把 `MCPManager` 这个核心类的每一行代码都摊开来看。你会看到我是怎么用 `AsyncExitStack` 管理多个 SSE 连接的生命周期，怎么做到某个服务挂了不影响其他服务，以及节点函数里那两个高频出现的辅助函数 `_call_mcp_tool` 和 `_extract_text_from_mcp` 到底做了什么。



## 一、什么是 MCP 协议

### 1. MCP 解决了什么问题

在传统的 Agent 架构里，调用外部工具通常是直接写 HTTP 请求或者函数调用，每接一个新服务就要写一套适配代码，工具数量一多就变得混乱。MCP 协议的核心思想是把"工具"这个概念标准化：

```
┌─────────────┐     MCP 协议      ┌─────────────────┐
│   Agent     │ ◄──────────────► │  MCP Server A   │
│  (Client)   │   统一接口        │  (bilibili)     │
│             │                  └─────────────────┘
│  list_tools │ ◄──────────────► ┌─────────────────┐
│  call_tool  │   统一接口        │  MCP Server B   │
└─────────────┘                  │  (rag)          │
                                 └─────────────────┘
                                 ┌─────────────────┐
                    统一接口      │  MCP Server C   │
              ◄──────────────►   │  (sql)          │
                                 └─────────────────┘
```

每个 MCP Server 暴露若干"工具"，每个工具有名字、描述和 `inputSchema`（参数结构），Agent 只需要通过 `list_tools()` 发现工具，通过 `call_tool()` 调用工具，完全不需要知道底层是查 SQL、做向量检索还是爬 B 站。

### 2. SSE 传输模式

MCP 支持多种传输方式，本项目使用的是 SSE（Server-Sent Events）模式。相比 WebSocket，SSE 更轻量，天然适合"请求-响应"的工具调用场景：

```
Client                          Server
  │                                │
  │── GET /sse ──────────────────► │  建立 SSE 长连接
  │◄─ text/event-stream ──────── │  服务端推送消息
  │                                │
  │── POST /messages ────────────► │  客户端发请求
  │◄─ SSE event (result) ──────── │  服务端推回结果
  │                                │
```

在代码里，我们用 `mcp` 库提供的 `sse_client` 来建立连接，它返回一对流 `(read_stream, write_stream)`，上层交给 `ClientSession` 封装成完整的 MCP 协议会话。


## 二、三个 MCP Server 的分工

我们的平台对接了一个内容分析系统（content-analysis-system），它对外暴露了三个 MCP Server，各司其职：

### 1. bilibili-mcp-server：9001

负责 B 站视频内容分析，比如视频元数据查询、UP 主信息、播放量统计等。端口 9001，SSE 路径 `/sse`。

### 2. rag-mcp-server：9002

语义检索服务，基于向量数据库做内容相似度匹配。给它一个问题，它返回最相关的文档片段和来源引用。端口 9002。

### 3. sql-mcp-server：9003

Text-to-SQL 服务，把自然语言问题转换成 SQL 查询，直接跑在结构化数据库上。端口 9003。

```
┌──────────────────────────────────────────────────────┐
│                    MCPManager                        │
│                                                      │
│  servers = {                                         │
│    "bilibili" ──► http://host:9001/sse               │
│    "rag"      ──► http://host:9002/sse               │
│    "sql"      ──► http://host:9003/sse               │
│  }                                                   │
│                                                      │
│  _sessions: dict[str, ClientSession]                 │
│  _connected: dict[str, bool]                         │
└──────────────────────────────────────────────────────┘
```

三个服务的 URL 全部从 `Config` 读取，不硬编码，方便环境切换。


## 三、MCPManager：统一管理多连接

`MCPManager` 是整个 MCP 层的核心，我把它的完整源码放上来，逐块分析。

### 1. 类结构设计

```python
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
```

三个核心成员变量：

| 变量 | 类型 | 作用 |
|------|------|------|
| `servers` | `dict[str, str]` | 服务名 → URL 的映射，连接配置 |
| `_sessions` | `dict[str, ClientSession]` | 服务名 → MCP 会话对象，实际通信用 |
| `_connected` | `dict[str, bool]` | 服务名 → 在线状态，用于快速判断是否可用 |
| `_exit_stack` | `AsyncExitStack` | 统一管理所有连接的生命周期 |

注意 `_sessions` 和 `_connected` 是分开的：`_connected[name] = False` 不代表 `_sessions` 里没有这个 key，而是明确标记"这个服务现在不可用，别尝试调用"。

### 2. AsyncExitStack 生命周期管理

`AsyncExitStack` 是 Python 标准库里的神器，专门管理多个异步上下文管理器。传统写法用 `async with` 嵌套三个 Server 会缩进四层，而 `AsyncExitStack` 可以把它们扁平化：

```python
stack = AsyncExitStack()
r1, w1 = await stack.enter_async_context(sse_client(url1))
s1 = await stack.enter_async_context(ClientSession(r1, w1))
r2, w2 = await stack.enter_async_context(sse_client(url2))
s2 = await stack.enter_async_context(ClientSession(r2, w2))
# 缩进只有一层，最后 await stack.aclose() 一次性清理全部
```

在 MCPManager 里，三个 Server 的连接全部注册到同一个 `_exit_stack`，调用 `close()` 时一把全关掉：

```python
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
```

`finally` 块确保即使 `aclose()` 抛异常，本地状态也会被清空，不留僵尸引用。


## 四、connect_all()：批量连接与优雅降级

这是 MCPManager 里最关键的方法，我一行一行讲。

### 1. 连接流程拆解

```python
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
```

每个 Server 的连接分三步：`sse_client()` 建立 SSE 长连接 → `ClientSession()` 封装 MCP 协议 → `session.initialize()` 执行握手。

两个 timeout 参数值得注意：`timeout=10` 是连接建立超时（10 秒连不上就放弃），`sse_read_timeout=300` 是 SSE 读超时（5 分钟没有事件才算超时，适应长连接场景）。

### 2. 失败不崩溃的设计哲学

`except Exception as e` 后面做的事情非常关键：**只标记 `_connected[name] = False`，不 `raise`**。

这意味着即使三个 MCP Server 全挂了，Agent 平台依然能正常启动。举个具体场景：rag Server 没启动，其他两个正常，`connect_all()` 执行后 `_connected = {"bilibili": True, "rag": False, "sql": True}`。用户问"桃姐对爱情怎么看？"，意图分类走 semantic，路由到 `query_rag`，`call_tool` 发现 rag 未连接，返回 `{"error": "MCP Server 'rag' 未连接", "isError": True}`，`merge_results` 输出友好提示——整个系统不崩溃。

这就是"优雅降级"：局部故障被隔离，系统整体可用。


## 五、list_tools()：动态工具发现

连接建立之后，我们并不预先知道每个 Server 有哪些工具。`list_tools()` 用于在运行时发现工具：

```python
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
```

两层防御：先检查 `session` 是否存在且 `_connected` 为 `True`（否则直接返回空列表），调用 `session.list_tools()` 抛异常时也返回空列表。返回的每个工具字典包含 `name`、`description` 和 `inputSchema`，是后面 `_call_mcp_tool` 智能选择工具的依据。


## 六、call_tool()：工具调用的封装

`call_tool()` 是最底层的调用接口，指定 Server、工具名、参数，拿回结果：

```python
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
```

返回格式统一是 `{"content": [...], "isError": bool}`，出错时是 `{"error": "...", "isError": True}`。这个格式是后续 `_extract_text_from_mcp()` 解析的依据，所以一定要保持一致。

注意 `c.model_dump()`——MCP SDK 返回的 `content` 是 Pydantic 模型列表，用 `model_dump()` 转成字典，方便 JSON 序列化。


## 七、_call_mcp_tool()：智能工具选择

`MCPManager` 提供了完整的底层能力，但节点函数（`query_sql`、`query_rag`）并不直接调用它，而是通过一个更高层的辅助函数 `_call_mcp_tool()`。这个函数加了一层"智能工具选择"逻辑：

```python
async def _call_mcp_tool(server_name: str, arguments: dict) -> dict:
    """通过 MCP 调用工具（自动发现工具名）

    如果 Server 只有一个工具，自动选择；
    如果有多个工具，尝试匹配常用名称。
    """
    from src.mcp_client.manager import get_mcp_manager

    mgr = get_mcp_manager()

    if not mgr._connected.get(server_name):
        return {"error": f"MCP Server '{server_name}' 未连接", "isError": True}

    # 发现可用工具
    tools = await mgr.list_tools(server_name)
    if not tools:
        return {"error": f"MCP Server '{server_name}' 无可用工具", "isError": True}

    # 自动选择工具：只有一个就直接用，多个则尝试常见名称
    if len(tools) == 1:
        tool_name = tools[0]["name"]
    else:
        # 尝试匹配常见工具名
        common_names = ["query", "search", "execute", "text_to_sql", "semantic_search"]
        tool_name = None
        for cn in common_names:
            for t in tools:
                if cn in t["name"].lower():
                    tool_name = t["name"]
                    break
            if tool_name:
                break
        # 都没匹配上，用第一个
        if not tool_name:
            tool_name = tools[0]["name"]

    return await mgr.call_tool(server_name, tool_name, arguments)
```

### 1. 单工具自动选中

如果一个 MCP Server 只暴露了一个工具（目前我们的三个 Server 都是这种情况），`len(tools) == 1` 直接选中，调用方完全不需要知道工具叫什么名字。这是最常见的路径。

### 2. 多工具常见名匹配

如果某个 Server 将来暴露了多个工具，代码会尝试从预定义的常见名列表里匹配：

```python
common_names = ["query", "search", "execute", "text_to_sql", "semantic_search"]
```

匹配逻辑是子字符串匹配（`cn in t["name"].lower()`），不是精确匹配，所以工具名叫 `semantic_search_v2` 也能被 `semantic_search` 命中。如果全部都没匹配上，兜底用第一个工具，保证不会空手而归。

这种"动态发现+智能选择"的设计，让节点函数完全解耦于工具名——MCP Server 端改了工具名，客户端代码不用动。


## 八、_extract_text_from_mcp()：结果提取

MCP 返回的结果是结构化的 `content` 列表，里面可能有 `text` 类型、`image` 类型等各种块。节点函数需要的是纯文本，所以有了这个提取函数：

```python
def _extract_text_from_mcp(result: dict) -> str:
    """从 MCP 调用结果中提取文本内容"""
    if result.get("isError"):
        return result.get("error", "MCP 调用出错")

    content = result.get("content", [])
    text_parts = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            text_parts.append(block.get("text", ""))
        elif isinstance(block, str):
            text_parts.append(block)

    return "\n".join(text_parts) if text_parts else "无返回内容"
```

处理逻辑分三层：

| 优先级 | 条件 | 行为 |
|--------|------|------|
| 1 | `isError == True` | 直接返回 `error` 字段的错误信息 |
| 2 | `content` 里有 `type == "text"` 的字典块 | 提取 `text` 字段 |
| 3 | `content` 里有纯字符串元素 | 直接拼接 |
| 4 | 以上都没匹配到 | 返回 `"无返回内容"` |

第 3 条是为了兼容一些返回格式不那么严格的 MCP Server，多一层容错。


## 九、全局单例：get_mcp_manager()

整个应用只有一个 MCPManager 实例，通过全局单例获取：

```python
_manager: Optional[MCPManager] = None

def get_mcp_manager() -> MCPManager:
    """获取 MCP 管理器实例"""
    global _manager
    if _manager is None:
        _manager = MCPManager()
    return _manager
```

延迟初始化的好处是模块导入时不会触发连接，只有真正需要时才创建实例。应用启动时调用 `connect_all()`，关闭时调用 `close()`，中间全靠 `_connected` 状态驱动。


## 十、完整调用链路图

把上面所有东西串起来，一次 MCP 调用的完整链路是这样的：

```
用户问题："播放量最高的视频是哪个？"
      │
      ▼
classify_intent (LLM 意图分类)
      │ route_type = "structured"
      ▼
route_query (条件路由)
      │ return "go_sql"
      ▼
query_sql (节点函数)
      │
      │  result = await _call_mcp_tool("sql", {
      │      "question": "播放量最高的视频是哪个？",
      │      "filters": {}
      │  })
      │
      ▼
_call_mcp_tool()
      │
      ├─ get_mcp_manager()       → 获取全局 MCPManager
      ├─ mgr._connected["sql"]   → True ✓
      ├─ mgr.list_tools("sql")   → [{"name": "text_to_sql", ...}]
      ├─ len(tools) == 1         → tool_name = "text_to_sql"
      └─ mgr.call_tool("sql", "text_to_sql", arguments)
              │
              ▼
         ClientSession.call_tool()
              │  (MCP JSON-RPC over SSE)
              ▼
         sql-mcp-server:9003
              │  Text-to-SQL → 执行 SQL → 返回结果
              ▼
         {"content": [{"type": "text", "text": "播放量最高..."}], "isError": false}
              │
              ▼
_extract_text_from_mcp(result)
      │ → "播放量最高的视频是..."
      ▼
query_sql 返回 {"sql_result": {"answer": "...", ...}}
      │
      ▼
merge_results (融合输出)
      │
      ▼
最终回答返回给用户
```

每一步都有错误检查，每一步失败都有兜底返回值。这就是整个 MCP 工具集成层的全貌。

## 总结

这篇文章从 MCP 协议的设计理念讲起，完整拆解了 `MCPManager` 的四个核心方法：`connect_all()` 负责批量连接和优雅降级，`list_tools()` 负责动态发现工具，`call_tool()` 负责底层调用封装，`close()` 负责统一资源清理。然后讲了节点函数里两个高频辅助函数：`_call_mcp_tool()` 做智能工具选择，`_extract_text_from_mcp()` 做结果文本提取。

核心设计要点回顾：
- **AsyncExitStack** 扁平化管理多个 SSE 连接的生命周期，避免嵌套地狱
- **优雅降级**：某个 MCP Server 挂了只标记离线，不影响其他服务和整体启动
- **动态工具发现**：不硬编码工具名，通过 `list_tools()` 运行时发现，兼容服务端变更
- **统一返回格式**：`{"content": [...], "isError": bool}`，所有调用方都按这个格式解析

下一篇文章，我们来讲 Agent 的记忆系统——ChromaDB 向量存储如何实现长期记忆和反思能力，让 Agent 在多次对话中越用越懂你。