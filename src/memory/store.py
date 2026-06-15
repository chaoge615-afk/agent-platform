"""记忆存储

Phase 14 实现：
- 短期记忆：对话上下文（LangGraph Checkpoint）
- 长期记忆：ChromaDB 向量存储
- 情景记忆：关键事件记录
- 反思机制：自我改进
"""
from typing import Optional
from src.config import Config


class MemoryStore:
    """记忆存储

    TODO: Phase 14 实现完整功能
    """

    def __init__(self):
        self.chroma_host = Config.CHROMA_HOST
        self.chroma_port = Config.CHROMA_PORT
        self.collection_name = Config.MEMORY_COLLECTION
        self._client = None

    async def connect(self):
        """连接 ChromaDB"""
        # TODO: 初始化 ChromaDB 客户端
        pass

    async def save_short_term(self, conversation_id: str, message: dict):
        """保存短期记忆（对话上下文）"""
        # TODO: 实现对话历史存储
        pass

    async def get_short_term(self, conversation_id: str, limit: int = 10) -> list:
        """获取短期记忆"""
        # TODO: 检索最近 N 轮对话
        return []

    async def save_long_term(self, user_id: str, memory: dict):
        """保存长期记忆（用户偏好）"""
        # TODO: 向量化存储到 ChromaDB
        pass

    async def search_long_term(self, query: str, top_k: int = 5) -> list:
        """语义检索长期记忆"""
        # TODO: ChromaDB 向量检索
        return []

    async def save_reflection(self, reflection: dict):
        """保存反思记录"""
        # TODO: 记录 Agent 的自我改进
        pass

    async def close(self):
        """关闭连接"""
        pass


# 全局实例
_store: Optional[MemoryStore] = None


def get_memory_store() -> MemoryStore:
    """获取记忆存储实例"""
    global _store
    if _store is None:
        _store = MemoryStore()
    return _store
