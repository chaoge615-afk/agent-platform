"""LangGraph Agent 节点函数

每个 Node 是一个函数：接收 State，返回 State 的部分更新。
LangGraph 会自动合并各 Node 的返回值到 State 中。
"""
import time
import json
import httpx
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from src.agent.state import AgentState
from src.config import Config


async def call_llm_direct(messages: list[dict]) -> str:
    """直接调用 LLM API（绕过 LangChain，完全控制请求头）

    用于需要自定义 X-Api-Key 头的场景。
    """
    headers = {
        "Content-Type": "application/json",
        "X-Api-Key": Config.ANTHROPIC_API_KEY,
    }

    # 构建 Anthropic 格式请求
    payload = {
        "model": Config.ANTHROPIC_MODEL,
        "messages": messages,
        "max_tokens": 1024,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{Config.ANTHROPIC_BASE_URL}/v1/messages",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        result = response.json()

        # 找到 type=text 的内容块（跳过 thinking 块）
        for block in result["content"]:
            if block.get("type") == "text":
                return block["text"]

        # 如果没有 text 块，返回第一个块的内容
        return result["content"][0].get("text", "")


def get_llm():
    """根据配置获取 LLM 实例

    支持两种提供者：
    - anthropic: Anthropic SDK（兼容 MiniMax 等）
    - openai: OpenAI SDK（兼容 DeepSeek 等）
    """
    if Config.LLM_PROVIDER == "anthropic":
        return ChatAnthropic(
            model=Config.ANTHROPIC_MODEL,
            api_key=Config.ANTHROPIC_API_KEY,
            base_url=Config.ANTHROPIC_BASE_URL,
            default_headers={"X-Api-Key": Config.ANTHROPIC_API_KEY},  # 兼容自定义代理
        )
    else:  # openai
        return ChatOpenAI(
            model=Config.OPENAI_MODEL,
            api_key=Config.OPENAI_API_KEY,
            base_url=Config.OPENAI_BASE_URL,
        )


# 意图分类 Prompt
INTENT_SYSTEM_PROMPT = """你是一个意图分类器。分析用户问题，判断应该使用哪种查询方式。

分类规则：
- structured: 需要结构化数据查询（统计、计数、排名、时间范围、特定UP主的视频数量等）
- semantic: 需要语义检索（观点、建议、看法、经验分享、情感话题等）
- hybrid: 同时需要结构化和语义（例如"桃姐最近聊了什么情感话题"）

同时提取过滤条件：
- up_name: UP主名称（如有）
- category: 分类（如有，从以下31个分类中选择：恋爱技巧, 婚姻经营, 分手挽回, 暧昧关系, 相亲约会, 情感心理, 两性关系, 家庭关系, 友情社交, 职场人际, 自我成长, 情绪管理, 沟通技巧, 信任建立, 冲突处理, 亲密关系, 情感依赖, 冷暴力, 出轨背叛, 离婚危机, 单身生活, 情感操控, 边界感, 安全感, 依恋类型, 情感成熟, 原生家庭, 性别差异, 情感表达, 关系修复, 情感疗愈）
- keywords: 关键话题词（列表）

以 JSON 格式返回：
{
    "route_type": "structured|semantic|hybrid",
    "filters": {
        "up_name": "xxx 或 null",
        "category": "xxx 或 null",
        "keywords": ["词1", "词2"]
    }
}"""


async def classify_intent(state: AgentState) -> dict:
    """意图分类节点

    调用 LLM 分析用户问题，判断路由类型和过滤条件。
    使用直接 HTTP 调用以支持自定义 X-Api-Key 头。
    """
    start = time.time()

    messages = [
        {"role": "user", "content": INTENT_SYSTEM_PROMPT + "\n\n用户问题：" + state["question"]},
    ]

    try:
        response_text = await call_llm_direct(messages)

        # 去除 markdown 代码块标记
        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        # 解析 JSON 响应
        result = json.loads(response_text)

        return {
            "route_type": result.get("route_type", "semantic"),
            "filters": result.get("filters", {}),
            "processing_time": time.time() - start,
        }
    except Exception as e:
        # 分类失败，降级到语义查询
        return {
            "route_type": "semantic",
            "filters": {},
            "error": f"意图分类失败，降级到语义查询: {str(e)}",
            "processing_time": time.time() - start,
        }
            "filters": {},
            "error": f"意图分类失败，降级到语义查询: {str(e)}",
            "processing_time": time.time() - start,
        }


def route_query(state: AgentState) -> str:
    """条件路由节点

    根据 route_type 决定下一步走哪个处理节点。
    返回值是 Edge 的名称，LangGraph 会跳转到对应的 Edge。
    """
    route_type = state.get("route_type", "semantic")

    if route_type == "structured":
        return "go_sql"
    elif route_type == "hybrid":
        return "go_both"
    else:
        return "go_rag"


def query_sql(state: AgentState) -> dict:
    """SQL 查询节点

    TODO: Phase 13 实现 MCP 调用
    当前为占位实现。
    """
    # TODO: 通过 MCP Client 调用 content-analysis-system 的 SQL MCP Server
    return {
        "sql_result": {
            "answer": "SQL 查询功能待实现（Phase 13: MCP 集成）",
            "data": [],
        }
    }


def query_rag(state: AgentState) -> dict:
    """RAG 查询节点

    TODO: Phase 13 实现 MCP 调用
    当前为占位实现。
    """
    # TODO: 通过 MCP Client 调用 content-analysis-system 的 RAG MCP Server
    return {
        "rag_result": {
            "answer": "RAG 查询功能待实现（Phase 13: MCP 集成）",
            "sources": [],
        }
    }


def merge_results(state: AgentState) -> dict:
    """结果融合节点

    将 SQL 和 RAG 的结果融合为最终回答。
    TODO: Phase 13 实现 LLM 融合
    """
    sql_result = state.get("sql_result", {})
    rag_result = state.get("rag_result", {})

    # 简单拼接（后续用 LLM 融合）
    parts = []
    sources = []

    if sql_result:
        parts.append(f"[结构化查询] {sql_result.get('answer', '')}")
    if rag_result:
        parts.append(f"[语义检索] {rag_result.get('answer', '')}")
        sources = rag_result.get("sources", [])

    return {
        "final_answer": "\n\n".join(parts) if parts else "暂无结果",
        "sources": sources,
    }
