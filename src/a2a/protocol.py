"""A2A (Agent-to-Agent) 协议实现

支持跨框架 Agent 协作：
- LangGraph Agent ↔ Multi-Agent Pipeline Agent
- 通过标准化协议实现互操作

核心概念：
- Agent Card: 能力声明
- Task: 任务管理
- Message: 消息交换
- Artifact: 结果产物
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class AgentCapability(BaseModel):
    """Agent 能力声明"""
    name: str = Field(..., description="能力名称")
    description: str = Field(..., description="能力描述")
    input_types: List[str] = Field(default_factory=list, description="支持的输入类型")
    output_types: List[str] = Field(default_factory=list, description="支持的输出类型")


class AgentCard(BaseModel):
    """Agent Card - Agent 身份和能力声明"""
    id: str = Field(..., description="Agent 唯一标识")
    name: str = Field(..., description="Agent 名称")
    version: str = Field(default="1.0.0", description="版本")
    description: str = Field(..., description="Agent 描述")
    capabilities: List[AgentCapability] = Field(default_factory=list, description="能力列表")
    endpoint: str = Field(..., description="Agent 服务端点")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class TaskState(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task(BaseModel):
    """A2A 任务"""
    id: str = Field(..., description="任务 ID")
    agent_id: str = Field(..., description="目标 Agent ID")
    input_data: Dict[str, Any] = Field(..., description="输入数据")
    state: TaskState = Field(default=TaskState.PENDING, description="任务状态")
    output_data: Optional[Dict[str, Any]] = Field(None, description="输出数据")
    error: Optional[str] = Field(None, description="错误信息")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class Message(BaseModel):
    """A2A 消息"""
    id: str = Field(..., description="消息 ID")
    task_id: str = Field(..., description="关联任务 ID")
    sender: str = Field(..., description="发送者")
    receiver: str = Field(..., description="接收者")
    content: str = Field(..., description="消息内容")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class Artifact(BaseModel):
    """A2A 产物（任务结果）"""
    id: str = Field(..., description="产物 ID")
    task_id: str = Field(..., description="关联任务 ID")
    name: str = Field(..., description="产物名称")
    content: Any = Field(..., description="产物内容")
    content_type: str = Field(default="text/plain", description="内容类型")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")


class TaskRequest(BaseModel):
    """任务请求"""
    input_data: Dict[str, Any]


class TaskResponse(BaseModel):
    """任务响应"""
    task_id: str
    state: str
    output_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ==================== Router Agent Card ====================

ROUTER_AGENT_CARD = AgentCard(
    id="router-agent-langgraph",
    name="Router Agent (LangGraph)",
    version="1.0.0",
    description="基于 LangGraph 的路由 Agent，支持意图分类、路由分发和结果融合",
    capabilities=[
        AgentCapability(
            name="intent_classification",
            description="意图分类（structured/semantic/hybrid）",
            input_types=["text"],
            output_types=["classification"],
        ),
        AgentCapability(
            name="query_routing",
            description="查询路由分发",
            input_types=["text", "classification"],
            output_types=["route_decision"],
        ),
        AgentCapability(
            name="result_fusion",
            description="多源结果融合",
            input_types=["sql_result", "rag_result"],
            output_types=["fused_answer"],
        ),
    ],
    endpoint="http://localhost:8001",
    metadata={
        "framework": "LangGraph",
        "features": ["SSE streaming", "Checkpoint", "Memory"],
    },
)


# ==================== Multi-Agent Pipeline Agent Card ====================

MULTI_AGENT_PIPELINE_CARD = AgentCard(
    id="router-agent-pipeline",
    name="Router Agent (Multi-Agent Pipeline)",
    version="1.0.0",
    description="基于 Multi-Agent Pipeline 的路由 Agent，支持复杂的多步骤任务",
    capabilities=[
        AgentCapability(
            name="complex_routing",
            description="复杂路由（多步骤、条件分支）",
            input_types=["text"],
            output_types=["route_plan"],
        ),
        AgentCapability(
            name="orchestration",
            description="多 Agent 编排",
            input_types=["task"],
            output_types=["orchestration_result"],
        ),
    ],
    endpoint="http://localhost:8000",
    metadata={
        "framework": "Multi-Agent Pipeline",
        "features": ["Multi-step", "Conditional routing"],
    },
)
