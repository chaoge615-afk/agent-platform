"""LangGraph Agent 节点函数

每个 Node 是一个函数：接收 State，返回 State 的部分更新。
LangGraph 会自动合并各 Node 的返回值到 State 中。

节点列表：
- classify_intent: 意图分类（LLM）
- route_query: 条件路由
- query_sql: 结构化查询（MCP → SQL Server）
- query_rag: 语义检索（MCP → RAG Server）
- query_both: 混合查询（并行 SQL + RAG）
- merge_results: 结果融合（LLM）
"""
import asyncio
import time
import json
import httpx
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from src.agent.state import AgentState
from src.config import Config


# ==================== LLM 调用工具 ====================


async def call_llm_direct(messages: list[dict]) -> str:
    """直接调用 LLM API，根据 LLM_PROVIDER 自动切换格式

    支持两种提供者：
    - anthropic: Anthropic /v1/messages 格式（兼容 MiniMax 等）
    - openai: OpenAI /chat/completions 格式（兼容 DeepSeek 等）
    """
    if Config.LLM_PROVIDER == "openai":
        # OpenAI 兼容格式
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Config.OPENAI_API_KEY}",
        }
        payload = {
            "model": Config.OPENAI_MODEL,
            "messages": messages,
            "max_tokens": 1024,
        }
        url = f"{Config.OPENAI_BASE_URL}/chat/completions"
    else:
        # Anthropic 兼容格式
        headers = {
            "Content-Type": "application/json",
            "X-Api-Key": Config.ANTHROPIC_API_KEY,
        }
        payload = {
            "model": Config.ANTHROPIC_MODEL,
            "messages": messages,
            "max_tokens": 1024,
        }
        url = f"{Config.ANTHROPIC_BASE_URL}/v1/messages"

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()

        if Config.LLM_PROVIDER == "openai":
            # OpenAI 格式: {"choices": [{"message": {"content": "..."}}]}
            return result["choices"][0]["message"]["content"]
        else:
            # Anthropic 格式: {"content": [{"type": "text", "text": "..."}]}
            # 跳过 thinking 块，只取 text 块
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


# ==================== MCP 调用辅助 ====================


async def _call_mcp_tool(server_name: str, arguments: dict) -> dict:
    """通过 MCP 调用工具（自动发现工具名）

    如果 Server 只有一个工具，自动选择；
    如果有多个工具，尝试匹配常用名称。

    K-16：_connected 失效或工具列举为空时，触发 manager 的惰性重连，
    单请求内自愈，而非恒返"无可用工具"。
    """
    from src.mcp_client.manager import get_mcp_manager

    mgr = get_mcp_manager()

    # not _connected 先尝试一次重连（manager.call_tool 内部也会兜底，
    # 但工具发现走 list_tools，需在此打通故障路径）
    if not mgr._connected.get(server_name):
        if not await mgr._reconnect(server_name):
            return {"error": f"MCP Server '{server_name}' 未连接", "isError": True}

    # 发现可用工具
    tools = await mgr.list_tools(server_name)
    if not tools:
        # list_tools 内部已自愈的话此处为空意味着真的没工具；
        # 但稳妥起见再兜底一次重连+重试
        if await mgr._reconnect(server_name):
            tools = await mgr.list_tools(server_name)
        if not tools:
            return {"error": f"MCP Server '{server_name}' 无可用工具", "isError": True}

    # 自动选择工具：只有一个就直接用，多个则尝试常见名称
    if len(tools) == 1:
        tool_name = tools[0]["name"]
    else:
        # 尝试匹配常见工具名
        common_names = ["query", "search", "execute", "text_to_sql", "semantic_search"]
        tool_name = None
        for cn in common_names:
            for t in tools:
                if cn in t["name"].lower():
                    tool_name = t["name"]
                    break
            if tool_name:
                break
        # 都没匹配上，用第一个
        if not tool_name:
            tool_name = tools[0]["name"]

    print(f"[DEBUG MCP] server={server_name}, tool={tool_name}, args_keys={list(arguments.keys())}")
    return await mgr.call_tool(server_name, tool_name, arguments)


def _extract_text_from_mcp(result: dict) -> str:
    """从 MCP 调用结果中提取文本内容"""
    if result.get("isError"):
        return result.get("error", "MCP 调用出错")

    content = result.get("content", [])
    text_parts = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            text_parts.append(block.get("text", ""))
        elif isinstance(block, str):
            text_parts.append(block)

    return "\n".join(text_parts) if text_parts else "无返回内容"


# ==================== 节点函数 ====================


# 意图分类 Prompt
INTENT_SYSTEM_PROMPT = """你是一个意图分类器。分析用户问题，判断应该使用哪种查询方式。

分类规则：
- structured: 纯结构化数据查询（统计、计数、排名、时间范围筛选、列表查询等）
  例："有多少个UP主？"、"播放量最高的视频"、"最近一周新增的视频"
- semantic: 纯语义检索（观点、建议、看法、经验分享、情感话题、沟通技巧等）
  例："如何维持长期关系？"、"有哪些关于人际关系的建议？"、"桃姐对爱情怎么看？"
- hybrid: 同时需要两种数据（用具体数字+观点来回答的问题）
  例："情感类视频的平均播放量是多少？这些视频主要讨论什么观点？"、"桃姐播放量最高的视频讲了什么？"

关键判断逻辑：
1. 如果问题只问"是什么观点/看法/建议" → semantic
2. 如果问题只问"多少/排名/列表" → structured
3. 如果问题同时需要"结构化数字（统计/计数/排名/时间/列表筛选）"和"观点"才能完整回答 → hybrid；
   注意：多个子句都只问观点/建议/话题内容时，即便有多个子句，也属于 semantic，不是 hybrid。
   只有当至少一个子句明确需要统计/计数/排名/列表筛选等结构化数字时才判 hybrid。
4. 提到特定UP主不等于hybrid，要看问的是什么
5. "什么话题/聊了什么"本身属语义检索；但若同一问题另有子句明确需要统计/计数/排名/列表筛选，则整体仍判 hybrid（以第3条为准）。

同时提取过滤条件：
- up_name: UP主名称（如有）
- category: 分类（如有）
- keywords: 关键话题词（列表）

以 JSON 格式返回：
{
    "route_type": "structured|semantic|hybrid",
    "filters": {
        "up_name": "xxx 或 null",
        "category": "xxx 或 null",
        "keywords": ["词1", "词2"]
    }
}

重要规则（对话上下文继承）：
- 如果对话历史中用户已经提到了特定UP主或话题，当前问题应继承这些上下文。
  例：用户先问"桃姐有几个视频"，再问"她最受欢迎的是哪个"，第二个问题的 filters 应继承 up_name="恋爱教头桃姐"。
- 如果当前问题是追问，filters 应继承上一轮的过滤条件。"""


async def classify_intent(state: AgentState) -> dict:
    """意图分类节点

    调用 LLM 分析用户问题，判断路由类型和过滤条件。
    使用直接 HTTP 调用以支持自定义 X-Api-Key 头。
    """
    start = time.time()

    # 构建 prompt（包含对话历史和反思上下文）
    prompt_parts = [INTENT_SYSTEM_PROMPT]

    # 注入对话历史（如果有）
    messages = state.get("messages") or []
    if messages:
        recent = messages[-6:]  # 最近 3 轮
        history = "\n".join(
            f"{'用户' if m.get('role') == 'user' else '助手'}: {m.get('content', '')}"
            for m in recent
        )
        prompt_parts.append(f"\n对话历史：\n{history}")

    # 注入长期记忆和反思上下文（如果有）
    memory_context = state.get("memory_context")
    if memory_context:
        prompt_parts.append(f"\n相关背景：\n{memory_context}")

    prompt_parts.append(f"\n\n用户问题：{state['question']}")

    messages_payload = [
        {"role": "user", "content": "\n".join(prompt_parts)},
    ]

    try:
        response_text = await call_llm_direct(messages_payload)

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

        elapsed_ms = (time.time() - start) * 1000
        route_type = result.get("route_type", "semantic")
        filters = result.get("filters", {})

        # 轻量后校验：闭合单次采样脆弱性（对抗审查修正建议 #4）
        # 规则：hybrid 须含至少一个结构化数字/排序子句。若模型判 hybrid
        # 但问题中不含任何结构化线索，视为误判，降级 semantic 并记审计。
        if route_type == "hybrid":
            _STRUCT_KW = (
                "多少", "几个", "数量", "排名", "最高", "最多", "最低", "最少",
                "最近一周", "最近一个月", "本周", "本月", "播放量", "点赞", "弹幕",
                "平均", "增长", "总计", "合计", "占比", "比例", "趋势",
            )
            if not any(k in state["question"] for k in _STRUCT_KW):
                try:
                    from src.security import log_event
                    log_event(
                        thread_id=state.get("conversation_id", "default"),
                        event_type="routing",
                        event_data={
                            "node": "classify_backstop",
                            "original_route": "hybrid",
                            "corrected_route": "semantic",
                            "reason": "no structured-number keyword in question",
                            "question": state["question"][:100],
                        },
                    )
                except Exception:
                    pass
                route_type = "semantic"

        # 记录审计日志
        try:
            from src.security import log_event
            log_event(
                thread_id=state.get("conversation_id", "default"),
                event_type="routing",
                event_data={
                    "node": "classify",
                    "route_type": route_type,
                    "filters": filters,
                    "question": state["question"][:100],
                },
                duration_ms=elapsed_ms,
            )
        except Exception:
            pass

        return {
            "route_type": route_type,
            "filters": filters,
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


async def query_sql(state: AgentState) -> dict:
    """SQL 查询节点

    通过 MCP 调用 content-analysis-system 的 SQL MCP Server，
    执行结构化数据查询（Text-to-SQL）。
    """
    start = time.time()
    question = state["question"]
    filters = state.get("filters") or {}

    try:
        result = await _call_mcp_tool("sql", {
            "question": question,
            "filters": filters,
        })

        answer_text = _extract_text_from_mcp(result)

        # 调试日志：帮助定位 SQL 链路问题
        print(f"[DEBUG query_sql] isError={result.get('isError')}, "
              f"answer_preview={answer_text[:200]}")

        # 记录审计日志
        try:
            from src.security import log_event
            log_event(
                thread_id=state.get("conversation_id", "default"),
                event_type="mcp_call",
                event_data={
                    "node": "query_sql",
                    "server": "sql",
                    "success": not result.get("isError"),
                    "answer_preview": answer_text[:100],
                },
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception:
            pass

        return {
            "sql_result": {
                "answer": answer_text,
                "data": result.get("content", []),
                "error": result.get("error") if result.get("isError") else None,
            }
        }
    except Exception as e:
        return {
            "sql_result": {
                "answer": f"SQL 查询异常: {str(e)}",
                "data": [],
                "error": str(e),
            }
        }


async def query_rag(state: AgentState) -> dict:
    """RAG 查询节点

    通过 MCP 调用 content-analysis-system 的 RAG MCP Server，
    执行语义检索。
    """
    start = time.time()
    question = state["question"]
    filters = state.get("filters") or {}

    try:
        result = await _call_mcp_tool("rag", {
            "question": question,
            "filters": filters,
            "top_k": 5,
        })

        answer_text = _extract_text_from_mcp(result)

        # 尝试从返回内容中提取 sources
        sources = []
        content = result.get("content", [])
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text", "")
                # 如果返回的是 JSON 字符串，尝试解析 sources
                try:
                    parsed = json.loads(text)
                    if isinstance(parsed, dict) and "sources" in parsed:
                        sources = parsed["sources"]
                except (json.JSONDecodeError, TypeError):
                    pass

        # 记录审计日志
        try:
            from src.security import log_event
            log_event(
                thread_id=state.get("conversation_id", "default"),
                event_type="mcp_call",
                event_data={
                    "node": "query_rag",
                    "server": "rag",
                    "success": not result.get("isError"),
                    "sources_count": len(sources),
                },
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception:
            pass

        return {
            "rag_result": {
                "answer": answer_text,
                "sources": sources,
                "error": result.get("error") if result.get("isError") else None,
            }
        }
    except Exception as e:
        return {
            "rag_result": {
                "answer": f"RAG 查询异常: {str(e)}",
                "sources": [],
                "error": str(e),
            }
        }


async def query_both(state: AgentState) -> dict:
    """混合查询节点

    并行执行 SQL 查询和 RAG 语义检索，适用于 hybrid 类型的问题。
    """
    sql_result, rag_result = await asyncio.gather(
        query_sql(state),
        query_rag(state),
    )
    return {**sql_result, **rag_result}


# 结果融合 Prompt
MERGE_SYSTEM_PROMPT = """你是一个信息融合专家。将结构化查询结果和语义检索结果融合，
生成一个连贯、完整的回答。

规则：
1. 优先使用结构化数据中的具体数字和事实
2. 用语义检索的内容补充观点、经验和上下文
3. 如果两部分结果有冲突，指出差异
4. 回答要简洁、有条理
5. 如果某一部分查询失败，只基于成功的部分回答
6. 如果两部分都失败，说明暂时无法获取相关信息"""

# K-15 修复：无效关键词列表补全（含"无可用工具"/"服务不可用"），
# 配合下方 _is_valid_result 用结构化 error 字段优先判断。
_INVALID_RESULT_KEYWORDS = ["待实现", "不可用", "无可用工具", "未连接", "异常", "服务不可用"]


def _is_valid_result(r: dict) -> bool:
    """判断 sql_result/rag_result 是否含有效内容。

    判据（结构化字段优先，关键词兜底）：
    - 有 answer 字段；且
    - 无 error/isError 标记；且
    - answer 不含已知无效关键词。
    """
    if not r or not r.get("answer"):
        return False
    if r.get("error") or r.get("isError"):
        return False
    ans = r.get("answer", "")
    return not any(k in ans for k in _INVALID_RESULT_KEYWORDS)


async def merge_results(state: AgentState) -> dict:
    """结果融合节点

    将 SQL 和 RAG 的结果融合为最终回答。
    - 只有一方结果时直接返回
    - 双方都有结果时用 LLM 融合
    - LLM 失败降级为简单拼接
    """
    sql_result = state.get("sql_result") or {}
    rag_result = state.get("rag_result") or {}

    has_sql = _is_valid_result(sql_result)
    has_rag = _is_valid_result(rag_result)

    # 只有一方有有效结果 → 直接返回
    if has_sql and not has_rag:
        return {
            "final_answer": sql_result.get("answer", ""),
            "sources": [],
        }
    if has_rag and not has_sql:
        return {
            "final_answer": rag_result.get("answer", ""),
            "sources": rag_result.get("sources", []),
        }

    # 两方都没有有效结果
    if not has_sql and not has_rag:
        # 返回原始结果（可能包含错误信息）
        parts = []
        if sql_result:
            parts.append(sql_result.get("answer", ""))
        if rag_result:
            parts.append(rag_result.get("answer", ""))
        return {
            "final_answer": "\n\n".join(parts) if parts else "暂无结果",
            "sources": [],
        }

    # 双方都有有效结果 → LLM 融合
    context_parts = []
    if has_sql:
        context_parts.append(f"[结构化查询结果]\n{sql_result.get('answer', '')}")
    if has_rag:
        context_parts.append(f"[语义检索结果]\n{rag_result.get('answer', '')}")

    messages = [
        {"role": "system", "content": MERGE_SYSTEM_PROMPT},
        {"role": "user", "content": f"用户问题：{state['question']}\n\n" + "\n\n".join(context_parts)},
    ]

    try:
        merged_text = await call_llm_direct(messages)
        return {
            "final_answer": merged_text,
            "sources": rag_result.get("sources", []),
        }
    except Exception as e:
        # LLM 融合失败，降级为简单拼接
        return {
            "final_answer": "\n\n".join(context_parts),
            "sources": rag_result.get("sources", []),
            "error": f"结果融合失败，使用简单拼接: {str(e)}",
        }


# ==================== 反思节点 ====================


# 反思 Prompt
REFLECT_PROMPT = """你是一个 AI 助手的质量改进模块。分析这次问答，提取可改进的洞察。

回答格式（JSON）：
{
    "should_save": true/false,
    "insight": "一句话总结的洞察或改进点（如果 should_save=true）",
    "type": "preference|correction|pattern|quality"
}

判断标准：
- should_save=true: 用户有明确偏好、纠正了错误、或发现了可复用的模式
- should_save=false: 普通问答，没有特别值得记录的洞察

如果没有值得记录的洞察，返回 should_save: false。
只返回 JSON，不要其他文字。"""


async def reflect(state: AgentState) -> dict:
    """反思节点

    分析问答质量，提取改进洞察存入 ChromaDB。
    反思结果会在未来的 classify_intent 中被检索，注入到分类 prompt 中。
    非关键路径：反思失败不影响主流程。
    """
    from src.memory.store import get_memory_store

    question = state.get("question", "")
    answer = state.get("final_answer", "")

    # 没有有效回答则跳过反思
    if not answer or answer == "暂无结果" or "未连接" in answer:
        return {}

    messages = [
        {"role": "system", "content": REFLECT_PROMPT},
        {"role": "user", "content": f"问题：{question}\n回答：{answer[:500]}"},
    ]

    try:
        response = await call_llm_direct(messages)
        response = response.strip()
        # 去除 markdown 代码块
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()

        result = json.loads(response)

        if result.get("should_save") and result.get("insight"):
            mem = get_memory_store()
            await mem.save_reflection({
                "content": result["insight"],
                "type": result.get("type", "general"),
                "question": question,
            })
    except Exception:
        # 反思失败是非关键路径，静默忽略
        pass

    return {}
