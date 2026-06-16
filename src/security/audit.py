"""审计日志 - 记录 Agent 决策和操作

功能：
1. 记录每次 Agent 决策的完整链路
2. 记录 LLM 调用（输入/输出/Token）
3. 记录 MCP 工具调用
4. 记录 HITL 决策
5. 支持查询和导出
"""
import json
import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from pydantic import BaseModel, Field


class AuditEntry(BaseModel):
    """审计日志条目"""
    id: Optional[int] = Field(None, description="日志 ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")
    thread_id: str = Field(..., description="对话线程 ID")
    event_type: str = Field(..., description="事件类型: llm_call/mcp_call/hitl/routing/answer")
    event_data: Dict[str, Any] = Field(..., description="事件数据")
    duration_ms: Optional[float] = Field(None, description="耗时（毫秒）")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class AuditLogger:
    """审计日志记录器"""

    def __init__(self, db_path: str = "./data/audit.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self._init_db()

    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                thread_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                event_data TEXT NOT NULL,
                duration_ms REAL,
                metadata TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_thread_id ON audit_logs(thread_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_event_type ON audit_logs(event_type)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_logs(timestamp)
        """)

        conn.commit()
        conn.close()

    def log(self, entry: AuditEntry):
        """记录日志"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO audit_logs (timestamp, thread_id, event_type, event_data, duration_ms, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            entry.timestamp.isoformat(),
            entry.thread_id,
            entry.event_type,
            json.dumps(entry.event_data, ensure_ascii=False),
            entry.duration_ms,
            json.dumps(entry.metadata, ensure_ascii=False),
        ))

        conn.commit()
        conn.close()

    def query(
        self,
        thread_id: Optional[str] = None,
        event_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[AuditEntry]:
        """查询日志"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = "SELECT id, timestamp, thread_id, event_type, event_data, duration_ms, metadata FROM audit_logs WHERE 1=1"
        params = []

        if thread_id:
            query += " AND thread_id = ?"
            params.append(thread_id)

        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)

        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())

        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        entries = []
        for row in rows:
            entries.append(AuditEntry(
                id=row[0],
                timestamp=datetime.fromisoformat(row[1]),
                thread_id=row[2],
                event_type=row[3],
                event_data=json.loads(row[4]),
                duration_ms=row[5],
                metadata=json.loads(row[6]) if row[6] else {},
            ))

        conn.close()
        return entries

    def export(self, output_path: str, **query_params):
        """导出日志到 JSON"""
        entries = self.query(**query_params)

        output_file = Path(output_path)
        output_file.parent.mkdir(exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(
                [entry.dict() for entry in entries],
                f,
                ensure_ascii=False,
                indent=2,
                default=str,
            )

        return len(entries)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 总日志数
        cursor.execute("SELECT COUNT(*) FROM audit_logs")
        total = cursor.fetchone()[0]

        # 按事件类型统计
        cursor.execute("""
            SELECT event_type, COUNT(*) as count
            FROM audit_logs
            GROUP BY event_type
            ORDER BY count DESC
        """)
        by_type = {row[0]: row[1] for row in cursor.fetchall()}

        # 按线程统计
        cursor.execute("""
            SELECT thread_id, COUNT(*) as count
            FROM audit_logs
            GROUP BY thread_id
            ORDER BY count DESC
            LIMIT 10
        """)
        top_threads = {row[0]: row[1] for row in cursor.fetchall()}

        # 平均耗时
        cursor.execute("SELECT AVG(duration_ms) FROM audit_logs WHERE duration_ms IS NOT NULL")
        avg_duration = cursor.fetchone()[0] or 0

        conn.close()

        return {
            "total_logs": total,
            "by_event_type": by_type,
            "top_threads": top_threads,
            "avg_duration_ms": round(avg_duration, 2),
        }


# 全局实例
audit_logger = AuditLogger()


def log_event(
    thread_id: str,
    event_type: str,
    event_data: Dict[str, Any],
    duration_ms: Optional[float] = None,
    metadata: Optional[Dict[str, Any]] = None,
):
    """记录事件（便捷函数）"""
    entry = AuditEntry(
        thread_id=thread_id,
        event_type=event_type,
        event_data=event_data,
        duration_ms=duration_ms,
        metadata=metadata or {},
    )
    audit_logger.log(entry)
