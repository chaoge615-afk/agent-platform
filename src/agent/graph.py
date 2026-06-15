"""LangGraph 工作流定义

将 Node 用 Edge 连接起来，形成 Agent 工作流。

工作流结构：
    classify_intent → [条件路由]
        → go_sql  → query_sql   → merge_results → END
        → go_rag  → query_rag   → merge_results → END
        → go_both → query_sql + query_rag → merge_results → END
"""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from src.agent.state import AgentState
from src.agent.nodes import (
    classify_intent,
    route_query,
    query_sql,
    query_rag,
    query_both,
    merge_results,
    reflect,
)


# 全局 Checkpointer（支持多轮对话状态持久化）
_checkpointer = MemorySaver()


def build_agent_graph():
    """构建 Agent 工作流

    返回编译好的 LangGraph，可以直接 .invoke() 调用。
    使用 MemorySaver 作为 checkpointer，支持多轮对话。
    """
    # 1. 创建 StateGraph
    graph = StateGraph(AgentState)

    # 2. 添加 Node
    graph.add_node("classify", classify_intent)
    graph.add_node("query_sql", query_sql)
    graph.add_node("query_rag", query_rag)
    graph.add_node("query_both", query_both)
    graph.add_node("merge", merge_results)
    graph.add_node("reflect", reflect)

    # 3. 设置入口
    graph.set_entry_point("classify")

    # 4. 添加 Edge
    # classify → 条件路由
    graph.add_conditional_edges(
        "classify",
        route_query,
        {
            "go_sql": "query_sql",
            "go_rag": "query_rag",
            "go_both": "query_both",  # hybrid 并行执行 SQL + RAG
        },
    )

    # query_sql → merge
    graph.add_edge("query_sql", "merge")

    # query_rag → merge
    graph.add_edge("query_rag", "merge")

    # query_both → merge
    graph.add_edge("query_both", "merge")

    # merge → reflect → END
    graph.add_edge("merge", "reflect")
    graph.add_edge("reflect", END)

    # 5. 编译（带 checkpointer 支持多轮对话）
    return graph.compile(checkpointer=_checkpointer)


# 全局实例（延迟初始化）
_agent_graph = None


def get_agent_graph():
    """获取 Agent 工作流实例（单例）"""
    global _agent_graph
    if _agent_graph is None:
        _agent_graph = build_agent_graph()
    return _agent_graph
