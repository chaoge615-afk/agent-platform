"""Agent Platform — FastAPI 入口"""
import time
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional

from src.config import Config
from src.agent import get_agent_graph
from src.mcp_client import manager as mcp_manager
from src.memory import store as memory_store
from src.a2a.server import router as a2a_router


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


app = FastAPI(
    title="Agent Platform",
    description="LangGraph + MCP + Memory 通用 Agent 平台",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# A2A 协议路由
app.include_router(a2a_router)


# ==================== 数据模型 ====================

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


# ==================== API 端点 ====================

@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "Agent Platform",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.get("/health", response_model=HealthResponse)
async def health():
    """健康检查"""
    mgr = mcp_manager.get_mcp_manager()
    mem = memory_store.get_memory_store()

    return HealthResponse(
        status="healthy",
        version="0.1.0",
        mcp_servers={
            name: {"url": url, "connected": mgr._connected.get(name, False)}
            for name, url in mgr.servers.items()
        },
        memory_ready=mem._client is not None,
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """智能问答

    LangGraph Agent 处理用户问题：
    1. 加载对话历史和记忆上下文
    2. 意图分类（structured / semantic / hybrid）
    3. 路由到对应查询节点
    4. 融合结果 + 反思
    5. 保存对话记录
    """
    start = time.time()
    conv_id = request.conversation_id or "default"
    mem = memory_store.get_memory_store()

    # 加载对话历史（短期记忆）
    history = await mem.get_short_term(conv_id, limit=10)

    # 检索相关反思（长期记忆）
    memory_context = ""
    try:
        reflections = await mem.search_reflections(request.question, top_k=2)
        if reflections:
            memory_context = "过往改进洞察：\n" + "\n".join(
                f"- {r['content']}" for r in reflections
            )
    except Exception:
        pass  # 记忆检索失败不影响主流程

    # 调用 LangGraph Agent
    graph = get_agent_graph()
    initial_state = {
        "question": request.question,
        "conversation_id": conv_id,
        "messages": history,
        "memory_context": memory_context,
    }
    config = {
        "configurable": {
            "thread_id": conv_id
        }
    }

    try:
        result = await graph.ainvoke(initial_state, config=config)

        # 保存本轮对话到短期记忆
        await mem.save_short_term(conv_id, {"role": "user", "content": request.question})
        await mem.save_short_term(conv_id, {"role": "assistant", "content": result.get("final_answer", "")})

        return ChatResponse(
            answer=result.get("final_answer", "无响应"),
            route_type=result.get("route_type"),
            sources=result.get("sources", []),
            processing_time=time.time() - start,
            error=result.get("error"),
        )
    except Exception as e:
        return ChatResponse(
            answer=f"处理失败: {str(e)}",
            processing_time=time.time() - start,
            error=str(e),
        )


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


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """智能问答（SSE 流式输出）

    逐节点推送 LangGraph 执行过程：
    - event: node_update — 每个节点执行完成后的状态更新
    - event: error — 执行出错
    - event: done — 全部完成
    """
    conv_id = request.conversation_id or "default"
    mem = memory_store.get_memory_store()

    # 加载对话历史和记忆上下文
    history = await mem.get_short_term(conv_id, limit=10)
    memory_context = ""
    try:
        reflections = await mem.search_reflections(request.question, top_k=2)
        if reflections:
            memory_context = "过往改进洞察：\n" + "\n".join(
                f"- {r['content']}" for r in reflections
            )
    except Exception:
        pass

    graph = get_agent_graph()
    initial_state = {
        "question": request.question,
        "conversation_id": conv_id,
        "messages": history,
        "memory_context": memory_context,
    }
    config = {
        "configurable": {
            "thread_id": conv_id
        }
    }

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
                    # 记录最终回答用于保存
                    if node_name == "merge" and "final_answer" in updates:
                        final_answer = updates["final_answer"]
                    event_data = {
                        "node": node_name,
                        "step": step,
                        "updates": _safe_serialize(updates),
                    }
                    yield f"event: node_update\ndata: {json.dumps(event_data, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

        # 保存本轮对话到短期记忆
        await mem.save_short_term(conv_id, {"role": "user", "content": request.question})
        if final_answer:
            await mem.save_short_term(conv_id, {"role": "assistant", "content": final_answer})

        # 最终完成事件
        elapsed = time.time() - start
        done_data = {
            "processing_time": round(elapsed, 2),
            "conversation_id": conv_id,
        }
        yield f"event: done\ndata: {json.dumps(done_data, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/mcp/tools")
async def list_mcp_tools():
    """列出所有 MCP Server 的工具"""
    mgr = mcp_manager.get_mcp_manager()
    tools = {}

    for server_name in mgr.servers:
        tools[server_name] = await mgr.list_tools(server_name)

    return {"tools": tools}


@app.get("/api/memory/stats")
async def memory_stats():
    """记忆系统统计"""
    mem = memory_store.get_memory_store()
    return await mem.get_stats()


# ==================== 审计日志 ====================

@app.get("/api/audit/stats")
async def audit_stats():
    """审计日志统计"""
    from src.security import audit_logger
    return audit_logger.get_stats()


@app.get("/api/audit/logs")
async def audit_logs(
    thread_id: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = 100,
):
    """查询审计日志"""
    from src.security import audit_logger

    logs = audit_logger.query(
        thread_id=thread_id,
        event_type=event_type,
        limit=limit,
    )

    return {
        "count": len(logs),
        "logs": [log.dict() for log in logs],
    }


@app.get("/api/audit/logs/{thread_id}")
async def audit_logs_by_thread(thread_id: str, limit: int = 100):
    """按线程查询审计日志"""
    from src.security import audit_logger

    logs = audit_logger.query(thread_id=thread_id, limit=limit)

    return {
        "thread_id": thread_id,
        "count": len(logs),
        "logs": [log.dict() for log in logs],
    }


# ==================== 启动 ====================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=Config.API_HOST,
        port=Config.API_PORT,
        reload=True,
    )
