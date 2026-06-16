"""A2A Client - 调用其他 A2A Agent"""
from typing import Dict, Any, Optional
import httpx

from src.a2a.protocol import AgentCard, TaskResponse


class A2AClient:
    """A2A 客户端"""

    def __init__(self, agent_card: AgentCard):
        self.agent_card = agent_card
        self.base_url = agent_card.endpoint

    async def get_agent_card(self) -> AgentCard:
        """获取远程 Agent Card"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{self.base_url}/a2a/agent-card")
            response.raise_for_status()
            return AgentCard(**response.json())

    async def create_task(self, input_data: Dict[str, Any]) -> TaskResponse:
        """创建任务"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/a2a/tasks",
                json={"input_data": input_data},
            )
            response.raise_for_status()
            return TaskResponse(**response.json())

    async def get_task(self, task_id: str) -> TaskResponse:
        """获取任务状态"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{self.base_url}/a2a/tasks/{task_id}")
            response.raise_for_status()
            return TaskResponse(**response.json())

    async def cancel_task(self, task_id: str) -> Dict[str, Any]:
        """取消任务"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.delete(f"{self.base_url}/a2a/tasks/{task_id}")
            response.raise_for_status()
            return response.json()

    async def list_tasks(self) -> Dict[str, Any]:
        """列出所有任务"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{self.base_url}/a2a/tasks")
            response.raise_for_status()
            return response.json()


class A2AOrchestrator:
    """A2A 编排器 - 协调多个 Agent"""

    def __init__(self):
        self.clients: Dict[str, A2AClient] = {}

    def register_agent(self, agent_card: AgentCard):
        """注册 Agent"""
        self.clients[agent_card.id] = A2AClient(agent_card)

    async def call_agent(
        self, agent_id: str, input_data: Dict[str, Any]
    ) -> TaskResponse:
        """调用指定 Agent"""
        if agent_id not in self.clients:
            raise ValueError(f"Agent {agent_id} not registered")

        client = self.clients[agent_id]
        return await client.create_task(input_data)

    async def route_by_capability(
        self, capability: str, input_data: Dict[str, Any]
    ) -> TaskResponse:
        """根据能力路由到合适的 Agent"""
        for agent_id, client in self.clients.items():
            try:
                card = await client.get_agent_card()
                for cap in card.capabilities:
                    if cap.name == capability:
                        return await client.create_task(input_data)
            except Exception:
                continue

        raise ValueError(f"No agent found with capability: {capability}")
