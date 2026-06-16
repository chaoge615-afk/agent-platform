"""记忆存储

三层记忆架构：
- 短期记忆：对话上下文（内存字典，每会话最多 50 条）
- 长期记忆：ChromaDB 嵌入式向量存储（语义检索）
- 反思记忆：Agent 自我改进洞察（ChromaDB 独立 collection）
"""
import os
import time
import uuid
from typing import Optional

import chromadb

from src.config import Config


class MemoryStore:
    """记忆存储

    使用 ChromaDB PersistentClient 做本地嵌入式向量存储，
    短期记忆用内存字典（配合 LangGraph Checkpoint 实现多轮对话）。
    """

    def __init__(self):
        self.data_path = Config.CHROMA_DATA_PATH
        self.collection_name = Config.MEMORY_COLLECTION
        self._client: Optional[chromadb.ClientAPI] = None
        self._long_term_collection = None
        self._reflection_collection = None
        # 短期记忆：{conversation_id: [messages]}
        self._short_term: dict[str, list] = {}

    async def connect(self):
        """初始化 ChromaDB 嵌入式客户端"""
        # 确保数据目录存在
        os.makedirs(self.data_path, exist_ok=True)

        # 使用 PersistentClient（本地嵌入式模式，无需外部服务）
        self._client = chromadb.PersistentClient(path=self.data_path)

        # 长期记忆 collection
        self._long_term_collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        # 反思记忆 collection
        self._reflection_collection = self._client.get_or_create_collection(
            name="agent_reflections",
            metadata={"hnsw:space": "cosine"},
        )

        print(f"[Memory] ChromaDB 已初始化: {self.data_path}")

    # ==================== 短期记忆（内存字典） ====================

    async def save_short_term(self, conversation_id: str, message: dict):
        """保存短期记忆（对话上下文）

        Args:
            conversation_id: 对话 ID
            message: {"role": "user"/"assistant", "content": "..."}
        """
        if conversation_id not in self._short_term:
            self._short_term[conversation_id] = []

        self._short_term[conversation_id].append({
            **message,
            "timestamp": time.time(),
        })

        # 每会话最多保留 50 条消息
        if len(self._short_term[conversation_id]) > 50:
            self._short_term[conversation_id] = self._short_term[conversation_id][-50:]

    async def get_short_term(self, conversation_id: str, limit: int = 10) -> list:
        """获取短期记忆（最近 N 条消息）"""
        messages = self._short_term.get(conversation_id, [])
        return messages[-limit:]

    # ==================== 长期记忆（ChromaDB 向量存储） ====================

    async def save_long_term(self, user_id: str, memory: dict):
        """保存长期记忆

        Args:
            user_id: 用户 ID
            memory: {"content": "...", "type": "preference/fact/pattern"}
        """
        if not self._long_term_collection:
            return

        doc = memory.get("content", "")
        metadata = {
            "user_id": user_id,
            "type": memory.get("type", "general"),
            "timestamp": time.time(),
        }
        mem_id = f"mem_{uuid.uuid4().hex[:12]}"

        self._long_term_collection.add(
            documents=[doc],
            metadatas=[metadata],
            ids=[mem_id],
        )

    async def search_long_term(self, query: str, top_k: int = 5) -> list:
        """语义检索长期记忆

        Args:
            query: 查询文本
            top_k: 返回结果数

        Returns:
            [{"content": "...", "metadata": {...}, "distance": float}]
        """
        if not self._long_term_collection:
            return []

        if self._long_term_collection.count() == 0:
            return []

        results = self._long_term_collection.query(
            query_texts=[query],
            n_results=min(top_k, self._long_term_collection.count()),
        )

        memories = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                memories.append({
                    "content": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else None,
                })
        return memories

    # ==================== 反思记忆 ====================

    async def save_reflection(self, reflection: dict):
        """保存反思记录

        Args:
            reflection: {"content": "...", "type": "...", "question": "..."}
        """
        if not self._reflection_collection:
            return

        doc = reflection.get("content", "")
        metadata = {
            "type": reflection.get("type", "general"),
            "question": reflection.get("question", ""),
            "timestamp": time.time(),
        }
        ref_id = f"ref_{uuid.uuid4().hex[:12]}"

        self._reflection_collection.add(
            documents=[doc],
            metadatas=[metadata],
            ids=[ref_id],
        )

    async def search_reflections(self, query: str, top_k: int = 3) -> list:
        """语义检索反思记录"""
        if not self._reflection_collection:
            return []

        if self._reflection_collection.count() == 0:
            return []

        results = self._reflection_collection.query(
            query_texts=[query],
            n_results=min(top_k, self._reflection_collection.count()),
        )

        reflections = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                reflections.append({
                    "content": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                })
        return reflections

    # ==================== 统计 ====================

    async def get_stats(self) -> dict:
        """获取记忆系统统计"""
        total_short = sum(len(msgs) for msgs in self._short_term.values())
        long_count = self._long_term_collection.count() if self._long_term_collection else 0
        ref_count = self._reflection_collection.count() if self._reflection_collection else 0

        return {
            "short_term_conversations": len(self._short_term),
            "short_term_messages": total_short,
            "long_term_count": long_count,
            "reflection_count": ref_count,
        }

    # ==================== 生命周期 ====================

    async def close(self):
        """关闭连接"""
        self._client = None
        self._long_term_collection = None
        self._reflection_collection = None


# 全局实例
_store: Optional[MemoryStore] = None


def get_memory_store() -> MemoryStore:
    """获取记忆存储实例"""
    global _store
    if _store is None:
        _store = MemoryStore()
    return _store
