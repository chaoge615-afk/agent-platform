"""Agent Platform — FastAPI 入口"""
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from src.config import Config
from src.agent import get_agent_graph
from src.mcp_client import manager as mcp_manager
from src.memory import store as memory_store


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
        mcp_servers={name: url for name, url in mgr.servers.items()},
        memory_ready=mem._client is not None,
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """智能问答

    LangGraph Agent 处理用户问题：
    1. 意图分类（structured / semantic / hybrid）
    2. 路由到对应查询节点
    3. 融合结果返回
    """
    start = time.time()

    # 调用 LangGraph Agent
    graph = get_agent_graph()
    initial_state = {
        "question": request.question,
        "conversation_id": request.conversation_id,
    }

    try:
        result = await graph.ainvoke(initial_state)

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

    return {
        "short_term_count": 0,  # TODO: 实现统计
        "long_term_count": 0,
        "reflection_count": 0,
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
