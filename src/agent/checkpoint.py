"""LangGraph Checkpoint 持久化

使用 SQLite 存储对话历史，支持多轮对话和状态恢复。
"""
import sqlite3
import json
from pathlib import Path
from typing import Optional, Any
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer


# 用于解码 writes 表里 langgraph 序列化的 channel 值（ormsgpack）。
# 或msgpack 是 langgraph-checkpoint 4.0.1 的硬依赖，无需新增依赖。
_SERDE = JsonPlusSerializer()

# 内部非数据通道，不参与 question/answer 回填
_INTERNAL_CHANNELS = ("__no_writes__",)


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
        """获取 SqliteSaver 实例（单例，同步）"""
        if self._saver is None:
            # 创建 SQLite 连接
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row

            # 创建 SqliteSaver
            self._saver = SqliteSaver(conn)

            # 初始化表结构
            self._saver.setup()

        return self._saver

    def get_async_saver(self) -> AsyncSqliteSaver:
        """获取 AsyncSqliteSaver 实例（用于 async graph.ainvoke）"""
        return AsyncSqliteSaver.from_conn_string(self.db_path)

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
        """获取线程的对话历史（每轮一条 turn）

        MS-01 修复：langgraph-checkpoint 4.0.1 把每个 channel 的写入存到独立的
        `writes` 表（thread_id/checkpoint_ns/checkpoint_id/task_id/idx/channel/
        type/value），值用 JsonPlusSerializer(ormsgpack) 序列化。top-level
        checkpoints.metadata.writes 在所有 ns='' 检查点里恒为空，旧代码读它
        导致 question/route_type/final_answer 全部回填失败。

        现改为：同时查 checkpoints + writes 两表，用 _SERDE.loads_typed 解码
        每个 channel 值，按 checkpoint_id 时序（UUID v1 单调递增）聚合：
        遇到 metadata.source=='input' 且 writes 含 'question' 通道时开新一轮 turn，
        把同一轮后续 loop 检查点的 route_type/final_answer/sources 回填到该 turn。
        最终每轮输出一条（对齐前端语义）。
        """
        conn = sqlite3.connect(self.db_path)

        # 1) 取该线程根命名空间（ns=''）的所有检查点，按时序升序
        ckpt_rows = conn.execute(
            """
            SELECT checkpoint_id, metadata
            FROM checkpoints
            WHERE thread_id = ? AND checkpoint_ns = ''
            ORDER BY checkpoint_id ASC
            """,
            (thread_id,)
        ).fetchall()

        # 2) 取该线程所有 writes 行，按 checkpoint_id 聚合成 {cid: {channel: value}}
        writes_by_cid: dict[str, dict[str, Any]] = {}
        wcur = conn.execute(
            "SELECT checkpoint_id, channel, type, value "
            "FROM writes WHERE thread_id = ? AND checkpoint_ns = ''",
            (thread_id,)
        )
        for cid, channel, wtype, value in wcur.fetchall():
            if channel in _INTERNAL_CHANNELS or channel.startswith("branch:"):
                continue
            bucket = writes_by_cid.setdefault(cid, {})
            try:
                # type=='null' 的通道值为 None
                bucket[channel] = None if wtype == "null" else _SERDE.loads_typed((wtype, value))
            except Exception:
                # 单个 channel 解码失败不影响整体回填
                bucket.setdefault(channel, None)

        conn.close()

        # 3) 按 checkpoint_id 时序聚合：显式跟踪 current_turn（不用 history[-1] 锚点，
        #    避免对抗审查指出的失效 Bug）。仅 input 检查点 append 一次 → 每轮一条。
        history: list[dict] = []
        current_turn: Optional[dict] = None

        for checkpoint_id, metadata_blob in ckpt_rows:
            metadata = json.loads(metadata_blob) if metadata_blob else {}
            w = writes_by_cid.get(checkpoint_id, {})
            q = w.get("question")
            rt = w.get("route_type")
            fa = w.get("final_answer")
            src = w.get("sources")

            if metadata.get("source") == "input" and q:
                # 新一轮 turn
                current_turn = {
                    "checkpoint_id": checkpoint_id,
                    "step": metadata.get("step"),
                    "source": "input",
                    "question": str(q),
                    "route_type": "",
                    "final_answer": "",
                    "sources": [],
                    "timestamp": checkpoint_id,  # checkpoint_id 即时序标识，兼容旧字段
                }
                history.append(current_turn)
            else:
                # 后续 loop 步：把 route_type/final_answer/sources 回填到当前轮
                if current_turn is not None:
                    if rt and not current_turn["route_type"]:
                        current_turn["route_type"] = str(rt)
                    if fa and not current_turn["final_answer"]:
                        current_turn["final_answer"] = str(fa)
                    if src and not current_turn["sources"]:
                        current_turn["sources"] = src if isinstance(src, list) else [src]

        return history


# 全局实例
_manager: Optional[CheckpointManager] = None


def get_checkpoint_manager() -> CheckpointManager:
    """获取 Checkpoint 管理器实例"""
    global _manager
    if _manager is None:
        _manager = CheckpointManager()
    return _manager
