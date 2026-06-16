"""A2A 模块"""
from src.a2a.protocol import (
    AgentCard,
    AgentCapability,
    Task,
    TaskState,
    Message,
    Artifact,
    ROUTER_AGENT_CARD,
    MULTI_AGENT_PIPELINE_CARD,
)
from src.a2a.server import router as a2a_router
from src.a2a.client import A2AClient, A2AOrchestrator

__all__ = [
    "AgentCard",
    "AgentCapability",
    "Task",
    "TaskState",
    "Message",
    "Artifact",
    "ROUTER_AGENT_CARD",
    "MULTI_AGENT_PIPELINE_CARD",
    "a2a_router",
    "A2AClient",
    "A2AOrchestrator",
]
