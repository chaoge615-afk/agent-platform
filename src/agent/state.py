"""LangGraph Agent 状态定义"""
from typing import TypedDict, Optional, Literal


class AgentState(TypedDict):
    """Agent 工作流状态

    LangGraph 的核心概念：所有 Node 共享同一个 State，
    每个 Node 读取 State、处理后写回 State。
    """
    # 输入
    question: str                          # 用户问题
    conversation_id: Optional[str]         # 对话 ID（用于记忆）

    # 对话历史（短期记忆）
    messages: Optional[list]               # [{role: "user"/"assistant", content: "..."}]

    # 长期记忆检索结果
    memory_context: Optional[str]          # 从 ChromaDB 检索到的相关记忆

    # 意图分类结果
    route_type: Optional[Literal["structured", "semantic", "hybrid"]]
    filters: Optional[dict]                # { up_name, category, keywords }

    # 各子系统结果
    sql_result: Optional[dict]             # Text-to-SQL 返回
    rag_result: Optional[dict]             # RAG 返回

    # 最终输出
    final_answer: Optional[str]            # 融合后的最终回答
    sources: Optional[list]                # 引用来源

    # 元数据
    error: Optional[str]                   # 错误信息
    processing_time: Optional[float]       # 处理耗时（秒）
