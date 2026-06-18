## 系列文章目录

[Agent 智能路由平台（一）：项目介绍与架构设计](./01-项目介绍与架构设计.md)
Agent 智能路由平台（二）：LangGraph 工作流引擎


### 文章目录

+ [系列文章目录](#_0)
+ [前言](#前言)
+ [一、为什么需要工作流引擎](#一为什么需要工作流引擎)
+ [二、StateGraph：声明式工作流](#二stategraph声明式工作流)
    + [1. 创建 StateGraph](#1-创建-stategraph)
    + [2. 添加节点](#2-添加节点)
    + [3. 设置入口和边](#3-设置入口和边)
    + [4. 条件路由](#4-条件路由)
    + [5. 编译与 Checkpointer](#5-编译与-checkpointer)
+ [三、节点函数：classify_intent](#三节点函数classify_intent)
    + [1. 分类 Prompt 设计](#1-分类-prompt-设计)
    + [2. 记忆上下文注入](#2-记忆上下文注入)
    + [3. JSON 解析与降级](#3-json-解析与降级)
+ [四、条件路由函数：route_query](#四条件路由函数route_query)
+ [五、节点函数：query_sql 与 query_rag](#五节点函数query_sql-与-query_rag)
    + [1. MCP 工具调用](#1-mcp-工具调用)
    + [2. 结果提取](#2-结果提取)
+ [六、节点函数：query_both 并行查询](#六节点函数query_both-并行查询)
+ [七、节点函数：merge_results 结果融合](#七节点函数merge_results-结果融合)
    + [1. 有效结果判断](#1-有效结果判断)
    + [2. LLM 融合](#2-llm-融合)
    + [3. 降级拼接](#3-降级拼接)
+ [八、节点函数：reflect 反思](#八节点函数reflect-反思)
    + [1. 反思 Prompt](#1-反思-prompt)
    + [2. 洞察存储](#2-洞察存储)
    + [3. 非关键路径设计](#3-非关键路径设计)
+ [九、LLM 调用策略](#九llm-调用策略)
    + [1. 直接 HTTP 调用](#1-直接-http-调用)
    + [2. LangChain 封装](#2-langchain-封装)
    + [3. thinking 模型处理](#3-thinking-模型处理)
+ [总结](#总结)




## 前言

上一篇讲了整体架构和技术选型，这篇来讲核心引擎——LangGraph 工作流。

LangGraph 是 LangChain 团队出的一个 Agent 编排框架，核心思想是**用图（Graph）来定义 Agent 的执行流程**。节点（Node）是函数，边（Edge）是控制流，条件边（Conditional Edge）是分支逻辑。

这篇会把工作流的定义、6 个节点函数的实现、LLM 调用策略全部拆开讲，包括分类 Prompt 怎么设计、并行查询怎么做、结果融合怎么降级、反思节点怎么实现自我改进。

[截图：LangGraph 工作流可视化——classify → route → query → merge → reflect]


## 一、为什么需要工作流引擎

在写 Agent 代码之前，我先试了"链式调用"的写法——一个函数调完调下一个：

```python
# 链式调用（反面教材）
async def handle_question(question):
    route_type = await classify(question)       # 1. 分类
    if route_type == "structured":
        result = await query_sql(question)      # 2a. SQL
    elif route_type == "hybrid":
        result = await query_both(question)     # 2b. 并行
    else:
        result = await query_rag(question)      # 2c. RAG
    answer = await merge(question, result)      # 3. 融合
    await reflect(question, answer)             # 4. 反思
    return answer
```

这个写法能跑，但问题很多：

1. **状态传递靠参数**：每个函数都要接收前面所有函数的结果，参数越来越多
2. **分支逻辑散落**：路由判断和业务逻辑混在一起，改一个要动好几个地方
3. **多轮对话难做**：要自己管 Checkpoint、自己管对话历史
4. **流式输出麻烦**：想逐节点推送进度，要自己写 SSE 生成器

LangGraph 把这些都抽象成了**声明式的图**：你只需要定义"有哪些节点"和"节点之间怎么连"，框架自动处理状态传递、Checkpoint、流式输出。


## 二、StateGraph：声明式工作流

### 1. 创建 StateGraph

LangGraph 的工作流从一个 `StateGraph` 开始，它接收一个类型定义作为参数：

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from src.agent.state import AgentState

graph = StateGraph(AgentState)
```

`AgentState` 是一个 `TypedDict`，定义了所有节点共享的状态字段。每个节点函数只需要返回它修改的那几个字段，LangGraph 会自动合并。

### 2. 添加节点

每个节点是一个 `async` 函数，接收完整的 State，返回部分更新：

```python
graph.add_node("classify", classify_intent)
graph.add_node("query_sql", query_sql)
graph.add_node("query_rag", query_rag)
graph.add_node("query_both", query_both)
graph.add_node("merge", merge_results)
graph.add_node("reflect", reflect)
```

注意 `route_query` 没有作为节点添加——它是一个**条件路由函数**，不处理数据，只返回下一步的方向。

### 3. 设置入口和边

```python
# 入口
graph.set_entry_point("classify")

# 固定边：query_sql → merge, query_rag → merge, query_both → merge
graph.add_edge("query_sql", "merge")
graph.add_edge("query_rag", "merge")
graph.add_edge("query_both", "merge")

# 固定边：merge → reflect → END
graph.add_edge("merge", "reflect")
graph.add_edge("reflect", END)
```

### 4. 条件路由

条件路由是 LangGraph 最有意思的功能之一。它接收一个函数和一组映射：

```python
graph.add_conditional_edges(
    "classify",          # 从 classify 节点出发
    route_query,         # 用这个函数的返回值做路由
    {
        "go_sql": "query_sql",    # 返回 "go_sql" → 跳到 query_sql
        "go_rag": "query_rag",    # 返回 "go_rag" → 跳到 query_rag
        "go_both": "query_both",  # 返回 "go_both" → 跳到 query_both
    },
)
```

`route_query` 函数的实现非常简单——就是一个 switch：

```python
def route_query(state: AgentState) -> str:
    route_type = state.get("route_type", "semantic")
    if route_type == "structured":
        return "go_sql"
    elif route_type == "hybrid":
        return "go_both"
    else:
        return "go_rag"
```

### 5. 编译与 Checkpointer

```python
_checkpointer = MemorySaver()

def build_agent_graph():
    graph = StateGraph(AgentState)
    # ... 添加节点和边 ...
    return graph.compile(checkpointer=_checkpointer)
```

`MemorySaver` 是 LangGraph 内置的内存 Checkpointer，它会在每个节点执行后保存完整的 State 快照。配合 `thread_id`，可以实现多轮对话——同一个 `thread_id` 的多次调用会共享状态。

```python
# 调用时传入 thread_id
config = {"configurable": {"thread_id": "conv-123"}}
result = await graph.ainvoke(initial_state, config=config)
```

编译好的图用单例模式管理，避免重复创建：

```python
_agent_graph = None

def get_agent_graph():
    global _agent_graph
    if _agent_graph is None:
        _agent_graph = build_agent_graph()
    return _agent_graph
```


## 三、节点函数：classify_intent

分类节点是整个工作流的入口，也是最重要的节点——分类错了，后面的查询全白搭。

### 1. 分类 Prompt 设计

分类 Prompt 是花了不少时间调试的。最关键的几个点：

```python
INTENT_SYSTEM_PROMPT = """你是一个意图分类器。分析用户问题，判断应该使用哪种查询方式。

分类规则：
- structured: 纯结构化数据查询（统计、计数、排名、时间范围筛选、列表查询等）
  例："有多少个UP主？"、"播放量最高的视频"、"最近一周新增的视频"
- semantic: 纯语义检索（观点、建议、看法、经验分享、情感话题、沟通技巧等）
  例："如何维持长期关系？"、"有哪些关于人际关系的建议？"
- hybrid: 同时需要两种数据（用具体数字+观点来回答的问题）
  例："情感类视频的平均播放量是多少？这些视频主要讨论什么话题？"

关键判断逻辑：
1. 如果问题只问"是什么观点/看法/建议" → semantic
2. 如果问题只问"多少/排名/列表" → structured
3. 如果问题同时需要数字和观点 → hybrid
4. 提到特定UP主不等于hybrid，要看问的是什么

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
}"""
```

第 4 条规则特别重要——"提到特定UP主不等于hybrid"。之前没有这条规则的时候，"桃姐关于吵架的建议是什么"会被分类为 hybrid（因为提到了桃姐），但实际上它只是 semantic。加了这条后准确率明显提升。

### 2. 记忆上下文注入

分类 Prompt 不是固定的，它会根据上下文动态拼接：

```python
async def classify_intent(state: AgentState) -> dict:
    prompt_parts = [INTENT_SYSTEM_PROMPT]

    # 注入对话历史（最近 3 轮）
    messages = state.get("messages") or []
    if messages:
        recent = messages[-6:]  # 最近 3 轮 = 6 条消息
        history = "\n".join(
            f"{'用户' if m.get('role') == 'user' else '助手'}: {m.get('content', '')}"
            for m in recent
        )
        prompt_parts.append(f"\n对话历史：\n{history}")

    # 注入反思记忆（从 ChromaDB 检索）
    memory_context = state.get("memory_context")
    if memory_context:
        prompt_parts.append(f"\n相关背景：\n{memory_context}")

    prompt_parts.append(f"\n\n用户问题：{state['question']}")
```

`memory_context` 是在 `main.py` 中预先检索的——用当前问题去 ChromaDB 的 `agent_reflections` collection 中搜索最相关的 2 条反思记录，拼接成"过往改进洞察"注入到 Prompt 中。

这是自我改进闭环的关键：**分类节点不仅看当前问题，还看历史上从类似问题中学到了什么**。

### 3. JSON 解析与降级

LLM 返回的 JSON 需要做一些清理：

```python
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

result = json.loads(response_text)
```

LLM 特别喜欢把 JSON 包在 ` ```json ` 和 ` ``` ` 里面，所以每次解析前都要先剥离代码块标记。

如果分类失败（JSON 解析错误或 LLM 调用失败），降级到 `semantic`：

```python
except Exception as e:
    return {
        "route_type": "semantic",
        "filters": {},
        "error": f"意图分类失败，降级到语义查询: {str(e)}",
    }
```

这个降级策略是基于实际使用频率选的——大多数用户问的都是语义类问题，降级到 semantic 至少能给出有用的回答。


## 四、条件路由函数：route_query

路由函数是最简单的函数——纯逻辑，不调用 LLM。注意它不是节点（没有通过 `add_node` 注册），而是传给 `add_conditional_edges` 的路由判断函数：

```python
def route_query(state: AgentState) -> str:
    """根据 route_type 决定下一步走哪个处理节点"""
    route_type = state.get("route_type", "semantic")
    if route_type == "structured":
        return "go_sql"
    elif route_type == "hybrid":
        return "go_both"
    else:
        return "go_rag"
```

默认值是 `"semantic"`，和 `classify_intent` 的降级策略一致。

这个函数虽然简单，但它是工作流的**分叉点**——LangGraph 根据它的返回值决定走哪条边。


## 五、节点函数：query_sql 与 query_rag

### 1. MCP 工具调用

SQL 和 RAG 查询节点都通过 MCP 协议调用外部服务。我封装了一个通用的 MCP 调用辅助函数：

```python
async def _call_mcp_tool(server_name: str, arguments: dict) -> dict:
    """通过 MCP 调用工具（自动发现工具名）"""
    mgr = get_mcp_manager()

    if not mgr._connected.get(server_name):
        return {"error": f"MCP Server '{server_name}' 未连接", "isError": True}

    # 发现可用工具
    tools = await mgr.list_tools(server_name)
    if not tools:
        return {"error": f"MCP Server '{server_name}' 无可用工具", "isError": True}

    # 自动选择工具
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
        if not tool_name:
            tool_name = tools[0]["name"]

    return await mgr.call_tool(server_name, tool_name, arguments)
```

这个函数做了一件很实用的事：**动态工具发现**。不需要硬编码工具名，启动时自动发现 MCP 服务暴露了哪些工具，然后智能选择。如果只有一个工具就直接用，多个则按常见名称匹配。

### 2. 结果提取

MCP 返回的结果是一组 content blocks，需要提取文本：

```python
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
```

query_sql 和 query_rag 的节点函数结构基本一样，区别只是调用的 MCP 服务名和参数不同：

```python
async def query_sql(state: AgentState) -> dict:
    result = await _call_mcp_tool("sql", {
        "question": question,
        "filters": filters,
    })
    answer_text = _extract_text_from_mcp(result)
    return {"sql_result": {"answer": answer_text, "data": result.get("content", [])}}

async def query_rag(state: AgentState) -> dict:
    result = await _call_mcp_tool("rag", {
        "question": question,
        "filters": filters,
        "top_k": 5,
    })
    answer_text = _extract_text_from_mcp(result)
    return {"rag_result": {"answer": answer_text, "sources": sources}}
```


## 六、节点函数：query_both 并行查询

混合查询是整个工作流中性能最敏感的部分。如果串行执行 SQL 和 RAG，总耗时是两者之和；并行执行则只取决于慢的那个。

```python
async def query_both(state: AgentState) -> dict:
    """混合查询节点：并行执行 SQL 和 RAG"""
    sql_result, rag_result = await asyncio.gather(
        query_sql(state),
        query_rag(state),
    )
    return {**sql_result, **rag_result}
```

就这么多。`asyncio.gather` 天然并行，两个查询同时发出，等两个都返回后合并结果。

实测效果：SQL 平均 2.5s，RAG 平均 3.2s，串行 5.7s，并行 3.3s，节省了约 42%。

[截图：性能对比表格——串行 vs 并行的耗时]


## 七、节点函数：merge_results 结果融合

### 1. 有效结果判断

融合之前先要判断哪些结果是有效的——MCP 服务可能返回错误，节点可能异常：

```python
async def merge_results(state: AgentState) -> dict:
    sql_result = state.get("sql_result") or {}
    rag_result = state.get("rag_result") or {}

    has_sql = bool(sql_result and sql_result.get("answer")
        and "待实现" not in sql_result.get("answer", "")
        and "不可用" not in sql_result.get("answer", "")
        and "异常" not in sql_result.get("answer", "")
        and "未连接" not in sql_result.get("answer", ""))
    has_rag = bool(rag_result and rag_result.get("answer")
        and "待实现" not in rag_result.get("answer", "")
        and "不可用" not in rag_result.get("answer", "")
        and "异常" not in rag_result.get("answer", "")
        and "未连接" not in rag_result.get("answer", ""))
```

用关键词匹配来判断有效性虽然不够优雅，但对于这个场景完全够用——MCP 返回的错误信息通常包含"待实现"、"不可用"、"异常"或"未连接"这样的关键词。

### 2. LLM 融合

如果 SQL 和 RAG 都有有效结果，用 LLM 来融合：

```python
MERGE_SYSTEM_PROMPT = """你是一个信息融合专家。将结构化查询结果和语义检索结果融合，
生成一个连贯、完整的回答。

规则：
1. 优先使用结构化数据中的具体数字和事实
2. 用语义检索的内容补充观点、经验和上下文
3. 如果两部分结果有冲突，指出差异
4. 回答要简洁、有条理
5. 如果某一部分查询失败，只基于成功的部分回答"""

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
merged_text = await call_llm_direct(messages)
```

### 3. 降级拼接

LLM 融合可能失败（超时、API 错误等），这时候降级为简单字符串拼接：

```python
try:
    merged_text = await call_llm_direct(messages)
    return {"final_answer": merged_text, "sources": rag_result.get("sources", [])}
except Exception as e:
    # LLM 融合失败，降级为简单拼接
    return {
        "final_answer": "\n\n".join(context_parts),
        "sources": rag_result.get("sources", []),
        "error": f"结果融合失败，使用简单拼接: {str(e)}",
    }
```

只有一方有有效结果的情况更简单——直接返回那一方，不需要融合：

```python
if has_sql and not has_rag:
    return {"final_answer": sql_result.get("answer", ""), "sources": []}
if has_rag and not has_sql:
    return {"final_answer": rag_result.get("answer", ""), "sources": rag_result.get("sources", [])}
```


## 八、节点函数：reflect 反思

反思节点是整个工作流中最有意思的部分——它让 Agent 具备了**自我改进**的能力。

### 1. 反思 Prompt

```python
REFLECT_PROMPT = """你是一个 AI 助手的质量改进模块。分析这次问答，提取可改进的洞察。

回答格式（JSON）：
{
    "should_save": true/false,
    "insight": "一句话总结的洞察或改进点",
    "type": "preference|correction|pattern|quality"
}

判断标准：
- should_save=true: 用户有明确偏好、纠正了错误、或发现了可复用的模式
- should_save=false: 普通问答，没有特别值得记录的洞察"""
```

注意 `should_save` 这个字段——不是每次问答都值得记录。普通的问题（"桃姐有几个视频"）不需要反思，只有用户纠正了错误、表达了偏好、或发现了可复用模式时才保存。

### 2. 洞察存储

如果 LLM 认为这次问答值得记录，洞察会存入 ChromaDB：

```python
result = json.loads(response)

if result.get("should_save") and result.get("insight"):
    mem = get_memory_store()
    await mem.save_reflection({
        "content": result["insight"],
        "type": result.get("type", "general"),
        "question": question,
    })
```

这些洞察会在未来的 `classify_intent` 中被语义检索出来，注入到分类 Prompt 中。比如如果之前记录了"用户倾向于把包含UP主名字的问题归类为 semantic 而非 hybrid"，下次遇到类似问题时，分类节点会参考这个洞察做出更准确的判断。

### 3. 非关键路径设计

反思节点有一个重要的设计原则：**反思失败不影响主流程**。

```python
try:
    response = await call_llm_direct(messages)
    # ... 解析和存储 ...
except Exception:
    # 反思失败是非关键路径，静默忽略
    pass

return {}  # 不更新任何状态
```

整个 `except` 块只有一个 `pass`。这是因为反思是锦上添花——如果 ChromaDB 挂了或 LLM 超时了，用户已经拿到回答了，不需要因为反思失败而报错。


## 九、LLM 调用策略

### 1. 直接 HTTP 调用

节点函数里的 LLM 调用没有用 LangChain，而是直接用 `httpx`：

```python
async def call_llm_direct(messages: list[dict]) -> str:
    """直接调用 LLM API（绕过 LangChain，完全控制请求头）"""
    headers = {
        "Content-Type": "application/json",
        "X-Api-Key": Config.ANTHROPIC_API_KEY,
    }

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

        # 找到 type=text 的内容块
        for block in result["content"]:
            if block.get("type") == "text":
                return block["text"]
```

为什么不用 LangChain？两个原因：
1. 需要自定义 `X-Api-Key` 头（公司内部代理需要）
2. 需要处理 thinking 模型的响应（LangChain 的封装有时处理不好）

### 2. LangChain 封装

另一个函数 `get_llm()` 用 LangChain 封装，适合需要 LangChain 生态的场景：

```python
def get_llm():
    """根据配置获取 LLM 实例"""
    if Config.LLM_PROVIDER == "anthropic":
        return ChatAnthropic(
            model=Config.ANTHROPIC_MODEL,
            api_key=Config.ANTHROPIC_API_KEY,
            base_url=Config.ANTHROPIC_BASE_URL,
            default_headers={"X-Api-Key": Config.ANTHROPIC_API_KEY},
        )
    else:
        return ChatOpenAI(
            model=Config.OPENAI_MODEL,
            api_key=Config.OPENAI_API_KEY,
            base_url=Config.OPENAI_BASE_URL,
        )
```

### 3. thinking 模型处理

直接 HTTP 调用中有一个细节——处理 thinking 模型：

```python
# 找到 type=text 的内容块（跳过 thinking 块）
for block in result["content"]:
    if block.get("type") == "text":
        return block["text"]
```

像 Claude 的思考模式，响应内容可能包含两种块：

```json
{
  "content": [
    {"type": "thinking", "thinking": "让我分析一下这个问题..."},
    {"type": "text", "text": "{\"route_type\": \"semantic\"}"}
  ]
}
```

如果不过滤，直接把整个 content 当文本用，就会把思考过程也混进去。所以代码里遍历 content blocks，只取 `type=text` 的块。


## 总结

LangGraph 把 6 个节点函数用声明式的图组织起来：`classify → route → query → merge → reflect`。每个节点是独立的纯函数，只关心自己的输入和输出。条件路由让分类结果自动分发到不同的查询路径，`asyncio.gather` 让混合查询并行执行，结果融合有 LLM 和拼接两级降级，反思节点在非关键路径上默默积累改进洞察。下一篇讲 MCP 协议集成——Agent 怎么通过 SSE 连接外部工具服务。
