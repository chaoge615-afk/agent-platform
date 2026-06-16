"""A2A Server - 将 LangGraph Agent 暴露为 A2A 服务"""
from typing import Dict, Any, Optional
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.a2a.protocol import (
    AgentCard,
    Task,
    TaskState,
    Message,
    Artifact,
    ROUTER_AGENT_CARD,
)
from src.agent import get_agent_graph


router = APIRouter(prefix="/a2a", tags=["A2A"])


class TaskRequest(BaseModel):
    """任务请求"""
    input_data: Dict[str, Any]


class TaskResponse(BaseModel):
    """任务响应"""
    task_id: str
    state: str
    output_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# 任务存储（内存）
_tasks: Dict[str, Task] = {}


@router.get("/agent-card", response_model=AgentCard)
async def get_agent_card():
    """获取 Agent Card（能力声明）"""
    return ROUTER_AGENT_CARD


@router.post("/tasks", response_model=TaskResponse)
async def create_task(request: TaskRequest):
    """创建 A2A 任务

    调用 LangGraph Agent 处理任务
    """
    task_id = str(uuid.uuid4())

    task = Task(
        id=task_id,
        agent_id=ROUTER_AGENT_CARD.id,
        input_data=request.input_data,
        state=TaskState.RUNNING,
    )
    _tasks[task_id] = task

    try:
        # 调用 LangGraph Agent
        question = request.input_data.get("question", "")
        if not question:
            raise ValueError("Missing 'question' in input_data")

        graph = get_agent_graph()
        initial_state = {
            "question": question,
            "conversation_id": request.input_data.get("conversation_id", "default"),
            "messages": [],
            "memory_context": "",
        }

        result = await graph.ainvoke(initial_state)

        task.state = TaskState.COMPLETED
        task.output_data = {
            "answer": result.get("final_answer", ""),
            "route_type": result.get("route_type"),
            "sources": result.get("sources", []),
        }
        task.updated_at = datetime.now()

        return TaskResponse(
            task_id=task_id,
            state=task.state.value,
            output_data=task.output_data,
        )

    except Exception as e:
        task.state = TaskState.FAILED
        task.error = str(e)
        task.updated_at = datetime.now()

        return TaskResponse(
            task_id=task_id,
            state=task.state.value,
            error=task.error,
        )


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    """获取任务状态和结果"""
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = _tasks[task_id]
    return TaskResponse(
        task_id=task_id,
        state=task.state.value,
        output_data=task.output_data,
        error=task.error,
    )


@router.delete("/tasks/{task_id}")
async def cancel_task(task_id: str):
    """取消任务"""
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = _tasks[task_id]
    if task.state in [TaskState.COMPLETED, TaskState.FAILED]:
        raise HTTPException(status_code=400, detail="Task already finished")

    task.state = TaskState.CANCELLED
    task.updated_at = datetime.now()

    return {"status": "cancelled", "task_id": task_id}


@router.get("/tasks")
async def list_tasks():
    """列出所有任务"""
    return {
        "tasks": [
            {
                "id": t.id,
                "state": t.state.value,
                "created_at": t.created_at.isoformat(),
                "updated_at": t.updated_at.isoformat(),
            }
            for t in _tasks.values()
        ]
    }
