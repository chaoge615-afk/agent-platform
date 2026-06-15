"""LangGraph Checkpoint 持久化

使用 SQLite 存储对话历史，支持多轮对话和状态恢复。
"""
import sqlite3
import json
from pathlib import Path
from typing import Optional, Any
from langgraph.checkpoint.sqlite import SqliteSaver


class CheckpointManager:
    """Checkpoint 管理器"""

    def __init__(self, db_path: str = "data/checkpoints.db"):
        self.db_path = db_path
        self._ensure_db_dir()
        self._saver = None

    def _ensure_db_dir(self):
        """确保数据库目录存在"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def get_saver(self) -> SqliteSaver:
        """获取 SqliteSaver 实例（单例）"""
        if self._saver is None:
            # 创建 SQLite 连接
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row

            # 创建 SqliteSaver
            self._saver = SqliteSaver(conn)

            # 初始化表结构
            self._saver.setup()

        return self._saver

    def get_thread_config(self, thread_id: str) -> dict:
        """获取线程配置"""
        return {"configurable": {"thread_id": thread_id}}

    def list_threads(self) -> list[str]:
        """列出所有对话线程"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT DISTINCT thread_id FROM checkpoints ORDER BY thread_id"
        )
        threads = [row[0] for row in cursor.fetchall()]
        conn.close()
        return threads

    def get_thread_history(self, thread_id: str) -> list[dict]:
        """获取线程的对话历史"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            """
            SELECT checkpoint_id, metadata, timestamp
            FROM checkpoints
            WHERE thread_id = ?
            ORDER BY timestamp ASC
            """,
            (thread_id,)
        )

        history = []
        for row in cursor.fetchall():
            metadata = json.loads(row[1]) if row[1] else {}
            history.append({
                "checkpoint_id": row[0],
                "question": metadata.get("question", ""),
                "route_type": metadata.get("route_type", ""),
                "timestamp": row[2]
            })

        conn.close()
        return history


# 全局实例
_manager: Optional[CheckpointManager] = None


def get_checkpoint_manager() -> CheckpointManager:
    """获取 Checkpoint 管理器实例"""
    global _manager
    if _manager is None:
        _manager = CheckpointManager()
    return _manager
