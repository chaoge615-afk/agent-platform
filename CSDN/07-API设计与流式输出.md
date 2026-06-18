## 系列文章目录

+ [Agent 智能路由平台（一）：项目介绍与架构设计](./01-项目介绍与架构设计.md)
+ [Agent 智能路由平台（二）：LangGraph 工作流引擎](./02-LangGraph工作流引擎.md)
+ [Agent 智能路由平台（三）：MCP 工具集成](./03-MCP工具集成.md)
+ [Agent 智能路由平台（四）：记忆系统](./04-记忆系统.md)
+ [Agent 智能路由平台（五）：安全与审计](./05-安全与审计.md)
+ [Agent 智能路由平台（六）：A2A 协议](./06-A2A协议.md)
+ Agent 智能路由平台（七）：API 设计与流式输出


### 文章目录

+ [系列文章目录](#_0)
+ [前言](#前言)
+ [一、FastAPI 生命周期与 CORS](#一fastapi-生命周期与-cors)
+ [二、Pydantic 数据模型](#二pydantic-数据模型)
+ [三、POST /api/chat 七步流程](#三post-apichat-七步流程)
+ [四、SSE 流式输出：POST /api/chat/stream](#四sse-流式输出post-apichatstream)
    + [1. 为什么选 SSE](#1-为什么选-sse)
    + [2. event_generator 实现](#2-event_generator-实现)
    + [3. SSE 事件协议](#3-sse-事件协议)
    + [4. _safe_serialize 安全序列化](#4-_safe_serialize-安全序列化)
+ [五、辅助端点与审计日志](#五辅助端点与审计日志)
+ [六、Config 类：双提供者配置](#六config-类双提供者配置)
+ [总结](#总结)




## 前言

这是 Agent 智能路由平台系列的最后一篇。前六篇从架构设计、LangGraph 工作流、MCP 工具集成、记忆系统、安全审计到 A2A 协议，把核心模块拆了个遍。这篇来收尾——**API 层怎么把前面所有东西串起来，暴露给前端调用**。

后端逻辑再精妙，最终都要通过 API 跟外界打交道。这个 API 层需要解决几个关键问题：启动时怎么初始化异步资源（MCP 连接池、向量数据库）？同步接口和流式接口怎么共存？LangGraph 的中间执行过程怎么实时推给前端？我选了 FastAPI + SSE（Server-Sent Events），把 `main.py` 和 `config.py` 逐行拆开讲。

GitHub 地址：https://github.com/chaoge615-afk/agent-platform


## 一、FastAPI 生命周期与 CORS

FastAPI 老版本用 `@app.on_event("startup/shutdown")`，已经被标记 deprecated。官方推荐 `lifespan` 上下文管理器——`yield` 之前是启动逻辑，之后是关闭逻辑，天然在同一个作用域里共享状态。

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动/关闭时的资源管理"""
    # 启动：初始化 MCP 连接和记忆系统
    print(f"[STARTUP] LLM_PROVIDER: {Config.LLM_PROVIDER}")
    print(f"[STARTUP] ANTHROPIC_BASE_URL: {Config.ANTHROPIC_BASE_URL}")
    print(f"[STARTUP] ANTHROPIC_API_KEY: {Config.ANTHROPIC_API_KEY[:10]}...")
    await mcp_manager.get_mcp_manager().connect_all()
    await memory_store.get_memory_store().connect()
    print("[OK] Agent Platform 启动完成")
    yield
    # 关闭：清理资源
    await mcp_manager.get_mcp_manager().close()
    await memory_store.get_memory_store().close()
    print("[BYE] Agent Platform 已关闭")
```

启动时做三件事：**打印配置摘要**（运维一眼就知道 API Key 配没配对）、**`connect_all()` 建立 3 个 MCP Server 的 SSE 长连接**、**`connect()` 初始化 ChromaDB**。`yield` 之后在 SIGTERM 时执行，断开连接、关闭向量库。

```
  uvicorn 启动 → 打印配置 → connect_all() (MCP x3) → connect() (ChromaDB)
                                                      │
                                                   yield (接受请求)
                                                      │
                              SIGTERM → close() (MCP) → close() (ChromaDB)
```

应用创建和中间件配置：

```python
app = FastAPI(
    title="Agent Platform",
    description="LangGraph + MCP + Memory 通用 Agent 平台",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# A2A 协议路由（第六篇）
app.include_router(a2a_router)
```

CORS 全开是开发阶段图方便，生产环境建议改成具体域名列表。`a2a_router` 挂载后，`/a2a/` 走 A2A 协议，`/api/` 走 REST API，互不干扰。


## 二、Pydantic 数据模型

```python
class ChatRequest(BaseModel):
    question: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    route_type: Optional[str] = None
    sources: Optional[list] = None
    processing_time: Optional[float] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    mcp_servers: dict
    memory_ready: bool
```

| 模型 | 核心字段 | 设计要点 |
|------|---------|---------|
| `ChatRequest` | `question`, `conversation_id` | 极简，`conversation_id` 不传默认 `"default"` |
| `ChatResponse` | `answer` + 4 个 Optional | 安全拦截返回时没有 `route_type`，异常时只有 `error` |
| `HealthResponse` | `mcp_servers`, `memory_ready` | 给 K8s readiness probe 用，暴露 MCP 连接状态 |


## 三、POST /api/chat 七步流程

这是整个平台最核心的同步接口。`docstring` 里已经写了 7 步：

```
  ChatRequest
       │
  ┌────▼─────────────┐
  │ 1. 输入安全检查    │ Guardrails 拦截
  └────┬─────────────┘
  ┌────▼──────────────┐
  │ 2. 加载历史+记忆    │ 短期记忆 + 长期反思
  └────┬──────────────┘
  ┌────▼─────────────┐
  │ 3. 记录请求日志    │ audit log
  └────┬─────────────┘
  ┌────▼─────────────┐
  │ 4. 调用 Agent     │ graph.ainvoke()
  └────┬─────────────┘
  ┌────▼─────────────┐
  │ 5. 输出过滤       │ PII 脱敏
  └────┬─────────────┘
  ┌────▼─────────────┐
  │ 6. 记录响应日志    │ audit log
  └────┬─────────────┘
  ┌────▼─────────────┐
  │ 7. 保存对话记录    │ 短期记忆
  └────┬─────────────┘
       │
  ChatResponse
```

先看守卫和记忆加载（步骤 1-3）：

```python
@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    start = time.time()
    conv_id = request.conversation_id or "default"

    # 步骤 1：输入安全检查
    from src.security import check_input, filter_output, log_event
    input_check = check_input(request.question)
    if not input_check.passed:
        log_event(thread_id=conv_id, event_type="guardrail",
                  event_data={"action": "input_blocked", "reason": input_check.reason,
                              "severity": input_check.severity})
        return ChatResponse(answer=f"抱歉，{input_check.reason}。请修改后重试。",
                            processing_time=time.time() - start, error=input_check.reason)

    # 步骤 2：加载对话历史 + 记忆上下文
    mem = memory_store.get_memory_store()
    history = await mem.get_short_term(conv_id, limit=10)
    memory_context = ""
    try:
        reflections = await mem.search_reflections(request.question, top_k=2)
        if reflections:
            memory_context = "过往改进洞察：\n" + "\n".join(f"- {r['content']}" for r in reflections)
    except Exception:
        pass  # 记忆检索失败不影响主流程

    # 步骤 3：记录请求审计日志
    log_event(thread_id=conv_id, event_type="chat_request",
              event_data={"question": request.question[:200]})
```

`import` 放在函数内部是故意的——`src.security` 依赖运行时初始化的组件，延迟导入避免循环依赖。`try/except + pass` 是刻意的——记忆是增强而非必需，ChromaDB 挂了主流程照走。

步骤 4-7，Agent 调用和收尾：

```python
    # 步骤 4：调用 LangGraph Agent
    graph = get_agent_graph()
    initial_state = {"question": request.question, "conversation_id": conv_id,
                     "messages": history, "memory_context": memory_context}
    config = {"configurable": {"thread_id": conv_id}}

    try:
        result = await graph.ainvoke(initial_state, config=config)
        final_answer = result.get("final_answer", "无响应")

        # 步骤 5：输出过滤（PII 脱敏）
        output_check = filter_output(final_answer)
        if output_check.modified_output:
            final_answer = output_check.modified_output

        # 步骤 6：记录响应审计日志
        log_event(thread_id=conv_id, event_type="answer",
                  event_data={"route_type": result.get("route_type"),
                              "answer_preview": final_answer[:200],
                              "sources_count": len(result.get("sources", []))},
                  duration_ms=(time.time() - start) * 1000)

        # 步骤 7：保存对话到短期记忆
        await mem.save_short_term(conv_id, {"role": "user", "content": request.question})
        await mem.save_short_term(conv_id, {"role": "assistant", "content": final_answer})

        return ChatResponse(answer=final_answer, route_type=result.get("route_type"),
                            sources=result.get("sources", []),
                            processing_time=time.time() - start, error=result.get("error"))
    except Exception as e:
        log_event(thread_id=conv_id, event_type="error",
                  event_data={"error": str(e)}, duration_ms=(time.time() - start) * 1000)
        return ChatResponse(answer=f"处理失败: {str(e)}",
                            processing_time=time.time() - start, error=str(e))
```

`graph.ainvoke()` 把 `initial_state` 喂给 LangGraph，跑完整个图：分类 → 路由 → 查询 → 融合 → 反思，返回终态。整个调用包在 `try/except` 里，出错不会 500，返回带 `error` 字段的 `ChatResponse`。


## 四、SSE 流式输出：POST /api/chat/stream

### 1. 为什么选 SSE

同步接口有个问题：LangGraph 跑完一次请求的节点链路（classify → query → merge → reflect，约 4 个节点）可能需要 10-30 秒，前端一直转圈白屏。

| 对比 | SSE | WebSocket |
|------|-----|-----------|
| 方向 | 单向（服务端→客户端） | 双向 |
| 协议 | 纯 HTTP | WS/WSS |
| 重连 | 浏览器自动重连 | 需自己实现 |
| 复杂度 | 低 | 高 |

我们的场景是 "前端发问题，服务端逐步推执行过程"——纯单向推送，SSE 完美匹配。

### 2. event_generator 实现

前半段（安全检查、记忆加载）和同步接口一样，核心区别在后半段：

```python
@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    # ... 前面和 /api/chat 一样 ...

    async def event_generator():
        start = time.time()
        step = 0
        final_answer = ""
        try:
            async for chunk in graph.astream(
                initial_state, config, stream_mode="updates"
            ):
                step += 1
                for node_name, updates in chunk.items():
                    # merge 节点产出最终回答时做 PII 过滤
                    if node_name == "merge" and "final_answer" in updates:
                        raw_answer = updates["final_answer"]
                        output_check = filter_output(raw_answer)
                        updates["final_answer"] = (
                            output_check.modified_output or raw_answer
                        )
                        final_answer = updates["final_answer"]
                    event_data = {
                        "node": node_name,
                        "step": step,
                        "updates": _safe_serialize(updates),
                    }
                    yield f"event: node_update\ndata: {json.dumps(event_data, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

        # 保存对话到短期记忆
        await mem.save_short_term(conv_id, {"role": "user", "content": request.question})
        if final_answer:
            await mem.save_short_term(conv_id, {"role": "assistant", "content": final_answer})

        # 审计日志
        elapsed = time.time() - start
        log_event(
            thread_id=conv_id, event_type="answer",
            event_data={"mode": "stream", "answer_preview": final_answer[:200] if final_answer else ""},
            duration_ms=elapsed * 1000,
        )

        # 完成事件
        done_data = {"processing_time": round(elapsed, 2), "conversation_id": conv_id}
        yield f"event: done\ndata: {json.dumps(done_data, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

关键在 `graph.astream(initial_state, config, stream_mode="updates")`。`stream_mode="updates"` 让 LangGraph 每个节点执行完就 yield 一次 `{node_name: state_updates}`。比如 classify_intent 跑完 yield `{"classify_intent": {"route_type": "hybrid"}}`，merge 跑完 yield `{"merge": {"final_answer": "..."}}`。前端收到后实时更新 UI 进度条。

### 3. SSE 事件协议

我定义了三种事件类型：

```
  event: node_update                    ← 每个节点执行完
  data: {"node":"classify_intent","step":1,"updates":{...}}

  event: error                          ← 出错
  data: {"error":"Connection timeout"}

  event: done                           ← 全部完成
  data: {"processing_time":3.42,"conversation_id":"abc"}
```

前端用 `fetch` + `ReadableStream` 消费（注意：`EventSource` 只支持 GET，而这个接口是 POST，所以要用 fetch）：

```javascript
const resp = await fetch('/api/chat/stream', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({question: '桃姐有几个视频？'}),
});
const reader = resp.body.getReader();
const decoder = new TextDecoder();
let buffer = '';
while (true) {
    const {done, value} = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, {stream: true});
    // 按 \n\n 分割 SSE 事件，解析 event/data 字段
    const parts = buffer.split('\n\n');
    buffer = parts.pop();
    for (const part of parts) {
        const event = part.match(/event: (.+)/)?.[1];
        const data = JSON.parse(part.match(/data: (.+)/)?.[1] || '{}');
        if (event === 'node_update') updateProgressUI(data);
        if (event === 'error') showError(data.error);
        if (event === 'done') { showResult(data); return; }
    }
}
```

`StreamingResponse` 的两个 header 不能少：`Cache-Control: no-cache` 禁止代理缓存事件流，`X-Accel-Buffering: no` 告诉 Nginx 别缓冲响应体。

**输入被拦截时也要走 SSE 格式**——用一个 `blocked_generator()` 推送 `error` + `done` 事件，保证前端 SSE 处理逻辑统一：

```python
    if not input_check.passed:
        async def blocked_generator():
            error_data = {"error": input_check.reason, "answer": f"抱歉，{input_check.reason}。"}
            yield f"event: error\ndata: {json.dumps(error_data, ensure_ascii=False)}\n\n"
            yield f"event: done\ndata: {json.dumps({'processing_time': 0}, ensure_ascii=False)}\n\n"
        return StreamingResponse(blocked_generator(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
```

### 4. _safe_serialize 安全序列化

LangGraph 节点返回的 updates 里可能有不可序列化的对象（LangChain Document、Pydantic model 等），直接 `json.dumps()` 会抛 `TypeError`：

```python
def _safe_serialize(obj) -> dict:
    """安全序列化对象为 JSON 兼容的 dict"""
    if isinstance(obj, dict):
        return {k: _safe_serialize(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_safe_serialize(item) for item in obj]
    elif isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    else:
        return str(obj)
```

递归遍历，基本类型原样返回，其他一律 `str()` 兜底。粗暴但有效——SSE 推送永远不会因序列化失败中断。


## 五、辅助端点与审计日志

除了核心聊天接口，还有几个辅助端点：

**GET /health**——健康检查，给 K8s 探针用：

```python
@app.get("/health", response_model=HealthResponse)
async def health():
    mgr = mcp_manager.get_mcp_manager()
    mem = memory_store.get_memory_store()
    return HealthResponse(status="healthy", version="0.1.0",
        mcp_servers={name: {"url": url, "connected": mgr._connected.get(name, False)}
                     for name, url in mgr.servers.items()},
        memory_ready=mem._client is not None)
```

返回 `{"mcp_servers":{"bilibili":{"connected":true},"sql":{"connected":false}},...}`，运维一眼就知道哪个 MCP Server 断了。

**GET /api/mcp/tools** 和 **GET /api/memory/stats**——遍历 MCP Server 列工具、返回向量库统计（文档数、反思条数、会话数）：

```python
@app.get("/api/mcp/tools")
async def list_mcp_tools():
    mgr = mcp_manager.get_mcp_manager()
    return {"tools": {name: await mgr.list_tools(name) for name in mgr.servers}}

@app.get("/api/memory/stats")
async def memory_stats():
    return await memory_store.get_memory_store().get_stats()
```

**审计日志三个端点**——全局统计、按条件过滤、按 thread_id 查链路：

```python
@app.get("/api/audit/stats")
async def audit_stats():
    from src.security import audit_logger
    return audit_logger.get_stats()

@app.get("/api/audit/logs")
async def audit_logs(thread_id: Optional[str] = None, event_type: Optional[str] = None, limit: int = 100):
    from src.security import audit_logger
    logs = audit_logger.query(thread_id=thread_id, event_type=event_type, limit=limit)
    return {"count": len(logs), "logs": [log.dict() for log in logs]}

@app.get("/api/audit/logs/{thread_id}")
async def audit_logs_by_thread(thread_id: str, limit: int = 100):
    from src.security import audit_logger
    logs = audit_logger.query(thread_id=thread_id, limit=limit)
    return {"thread_id": thread_id, "count": len(logs), "logs": [log.dict() for log in logs]}
```

支持追溯任何一次问答的完整链路——从 `chat_request` 到 `answer`（或 `error`），中间有没有 `guardrail` 拦截。


## 六、Config 类：双提供者配置

`config.py` 很短但很重要——所有配置项走环境变量，用 `python-dotenv` 加载 `.env`：

```python
class Config:
    LLM_PROVIDER: Literal["anthropic", "openai"] = os.getenv("LLM_PROVIDER", "anthropic")

    # Anthropic 兼容接口（Anthropic / MiniMax / 其他）
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_BASE_URL: str = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

    # OpenAI 兼容接口（OpenAI / DeepSeek / MiniMax / 其他）
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")

    # MCP Server 地址（B站 / RAG / SQL）
    BILIBILI_MCP_URL: str = os.getenv("BILIBILI_MCP_URL", "http://localhost:9001/sse")
    RAG_MCP_URL: str = os.getenv("RAG_MCP_URL", "http://localhost:9002/sse")
    SQL_MCP_URL: str = os.getenv("SQL_MCP_URL", "http://localhost:9003/sse")

    # 记忆系统 + LangSmith + 服务配置
    CHROMA_DATA_PATH: str = os.getenv("CHROMA_DATA_PATH", "./data/chroma_db")
    LANGCHAIN_TRACING_V2: bool = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8001"))
```

| 配置分组 | 关键字段 | 说明 |
|---------|---------|------|
| LLM 提供者 | `LLM_PROVIDER` | `Literal["anthropic", "openai"]`，运行时决定调用路径 |
| Anthropic 兼容 | `API_KEY` / `BASE_URL` / `MODEL` | 兼容 Claude、MiniMax 等 |
| OpenAI 兼容 | `API_KEY` / `BASE_URL` / `MODEL` | 兼容 GPT、DeepSeek 等 |
| MCP Server | 3 个 URL | B站 / RAG / SQL 各一个 SSE 端点 |

Config 是纯静态类，没有 `__init__`，全是类属性，直接 `Config.LLM_PROVIDER` 访问。启动入口 `uvicorn.run("src.main:app", host=Config.API_HOST, port=Config.API_PORT, reload=True)` 监听 `0.0.0.0:8001`。


## 总结

这是系列的最后一篇，做个全面回顾。整个 Agent Platform 做了一件事：**让用户用自然语言提问，系统自动判断意图、路由到合适的查询通道、融合结果、反思改进**。

七篇文章对应七个核心模块：

| 篇目 | 核心内容 | 关键词 |
|------|---------|--------|
| 一、项目介绍与架构设计 | 整体架构、技术选型、数据流 | LangGraph + MCP + ChromaDB |
| 二、LangGraph 工作流引擎 | StateGraph 定义、6 个节点函数 | 分类→路由→查询→融合→反思 |
| 三、MCP 工具集成 | SSE 长连接、工具调用协议 | stdio/SSE transport |
| 四、记忆系统 | 三层记忆、反思闭环 | 短期/长期/反思 |
| 五、安全与审计 | 输入护栏、PII 脱敏、审计链 | Guardrails + Audit |
| 六、A2A 协议 | Agent 间通信、任务委托 | REST over HTTP |
| 七、API 设计与流式输出 | FastAPI 生命周期、SSE 推送 | lifespan + astream |

几个我觉得做得比较满意的设计：

1. **工作流编排**——LangGraph StateGraph 声明式串起 6 个步骤，条件路由 + `asyncio.gather` 并行查询，比手写状态机清晰太多。
2. **反思闭环**——每次问答后自动提取改进洞察存入向量库，下次注入分类 Prompt，越用越准。
3. **SSE 流式输出**——`graph.astream()` 节点级进度实时推送，用户不用干等 30 秒白屏。
4. **安全纵深**——输入检查 → LLM 处理 → 输出过滤，三层安全是 API 层内建逻辑，审计全链路可追溯。

也有可以改进的地方：生产环境要加 JWT 认证和 rate limiting，以及——前端还没做（笑）。

如果你从头跟到了这里，感谢阅读。项目代码在 GitHub：https://github.com/chaoge615-afk/agent-platform ，欢迎 star、fork、提 issue。

我们下个项目见。
