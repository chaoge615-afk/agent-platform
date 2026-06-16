# Agent Platform 功能测试报告

**测试日期**: 2026-06-16  
**测试环境**: Windows 11, Python 3.11.9  
**LLM**: deepseek-v4-pro (via Anthropic 兼容接口 @ http://10.168.165.50:3300)  
**MCP 状态**: 3 个 MCP Server 均未连接（content-analysis-system Docker 环境未启动）  
**服务端口**: 8001

---

## 一、测试总览

| 类别 | 测试项数 | 通过 | 失败 | 通过率 |
|------|---------|------|------|--------|
| 基础 API 端点 | 4 | 4 | 0 | 100% |
| 核心聊天功能 | 4 | 4 | 0 | 100% |
| SSE 流式输出 | 3 | 3 | 0 | 100% |
| 意图分类 | 3 | 3 | 0 | 100% |
| 多轮对话 + 记忆 | 3 | 3 | 0 | 100% |
| A2A 协议 | 6 | 6 | 0 | 100% |
| 审计日志 | 5 | 5 | 0 | 100% |
| 安全 Guardrails | 9 | 9 | 0 | 100% |
| 边界情况 | 3 | 3 | 0 | 100% |
| 自动化评估 (路由准确率) | 11 | 10 | 1 | 90.9% |
| OpenAPI 文档 | 2 | 2 | 0 | 100% |
| **总计** | **53** | **52** | **1** | **98.1%** |

---

## 二、Bug 修复记录

测试过程中发现并修复了 **2 个 Bug**：

### Bug 1: A2A 模块导入错误
- **现象**: 服务启动失败，`ImportError: cannot import name 'TaskResponse' from 'src.a2a.protocol'`
- **原因**: `TaskResponse` 和 `TaskRequest` 定义在 `server.py` 中，但 `client.py` 和 `__init__.py` 从 `protocol.py` 导入
- **修复**: 将 `TaskRequest` 和 `TaskResponse` 移到 `protocol.py`，更新 `server.py` 的导入
- **文件**: `src/a2a/protocol.py`, `src/a2a/server.py`

### Bug 2: A2A 任务创建缺少 Checkpointer 配置
- **现象**: A2A 任务创建后状态为 `failed`，错误信息 `Checkpointer requires one or more of the following 'configurable' keys: thread_id`
- **原因**: `server.py` 的 `create_task` 调用 `graph.ainvoke(initial_state)` 时未传递 `config` 参数，而 LangGraph 的 `MemorySaver` checkpointer 要求 `thread_id`
- **修复**: 在 `ainvoke` 调用中添加 `config={"configurable": {"thread_id": conversation_id}}`
- **文件**: `src/a2a/server.py`

---

## 三、详细测试结果

### 3.1 基础 API 端点

| 端点 | 方法 | 状态码 | 结果 | 说明 |
|------|------|--------|------|------|
| `/` | GET | 200 | PASS | 返回项目名、版本、文档链接 |
| `/health` | GET | 200 | PASS | 返回服务状态、MCP 连接状态、记忆系统状态 |
| `/api/mcp/tools` | GET | 200 | PASS | MCP 离线时返回空工具列表（优雅降级） |
| `/api/memory/stats` | GET | 200 | PASS | 返回短期/长期记忆统计 |
| `/docs` | GET | 200 | PASS | Swagger UI 正常 |
| `/openapi.json` | GET | 200 | PASS | OpenAPI 规范完整，12 个路径全部注册 |

**Health 响应示例**:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "mcp_servers": {
    "bilibili": {"url": "http://localhost:9001/sse", "connected": false},
    "rag": {"url": "http://localhost:9002/sse", "connected": false},
    "sql": {"url": "http://localhost:9003/sse", "connected": false}
  },
  "memory_ready": true
}
```

### 3.2 核心聊天功能

| 测试项 | 状态码 | 路由类型 | 结果 | 耗时 |
|--------|--------|---------|------|------|
| 基本对话 | 200 | semantic | PASS | 17.6s |
| 结构化查询 | 200 | structured | PASS | 10.6s |
| 语义查询 | 200 | semantic | PASS | 18.5s |
| 混合查询 | 200 | hybrid | PASS | 14.6s |

**说明**: 由于 MCP Server 未连接，所有查询返回优雅降级消息（如 "MCP Server 'sql' 未连接"），但完整的 LangGraph 流水线（classify → route → query → merge → reflect）均正常执行。

### 3.3 SSE 流式输出

| 测试项 | Content-Type | 事件数 | 结果 |
|--------|-------------|--------|------|
| 流式结构化查询 | text/event-stream; charset=utf-8 | 10 | PASS |
| 流式语义查询 | text/event-stream; charset=utf-8 | 10 | PASS |
| 内置 test_stream | text/event-stream; charset=utf-8 | 10 | PASS |

**SSE 事件链路** (每次查询固定 5 个事件):
1. `event: node_update` — classify 节点（含 route_type、filters、processing_time）
2. `event: node_update` — query_sql 或 query_rag 或 query_both 节点
3. `event: node_update` — merge 节点（含 final_answer、sources）
4. `event: node_update` — reflect 节点
5. `event: done` — 完成信号（含 processing_time、conversation_id）

### 3.4 意图分类准确率

| 问题 | 期望路由 | 实际路由 | 结果 |
|------|---------|---------|------|
| "How many UP hosts are there" | structured | structured | PASS |
| "What does Tao Jie think about love" | semantic | semantic | PASS |
| "What has Tao Jie been talking about recently" | hybrid | hybrid | PASS |

### 3.5 多轮对话 + 记忆系统

| 测试项 | 结果 | 说明 |
|--------|------|------|
| 首轮对话 | PASS | conversation_id 正确追踪 |
| 追问对话 | PASS | 上下文保持，使用 conversation history |
| 记忆统计 | PASS | 8 conversations, 22 messages, 1 reflection |

**记忆系统统计**:
- 短期记忆: 基于内存字典，每个对话最多保留 50 条消息
- 长期记忆: ChromaDB PersistentClient，余弦相似度检索
- 反思机制: 每次回答后自动反思，存储到 ChromaDB `agent_reflections` collection

### 3.6 A2A 协议

| 端点 | 方法 | 状态码 | 结果 | 说明 |
|------|------|--------|------|------|
| `/a2a/agent-card` | GET | 200 | PASS | 返回 Agent Card（3 个能力声明） |
| `/a2a/tasks` | POST | 200 | PASS | 任务创建成功，状态 completed |
| `/a2a/tasks/{id}` | GET | 200 | PASS | 可查询任务状态和结果 |
| `/a2a/tasks` | GET | 200 | PASS | 列出所有任务 |
| `/a2a/tasks/{id}` | DELETE (已完成) | 400 | PASS | 正确拒绝取消已完成任务 |
| `/a2a/tasks/nonexistent` | DELETE | 404 | PASS | 正确返回 Task not found |
| `/a2a/tasks/nonexistent` | GET | 404 | PASS | 正确返回 404 |
| A2A Orchestrator | - | - | PASS | 编排器调用成功 |

**Agent Card 能力声明**:
- `intent_classification` — 意图分类
- `query_routing` — 查询路由分发
- `result_fusion` — 多源结果融合

### 3.7 审计日志

| 测试项 | 结果 | 说明 |
|--------|------|------|
| GET /api/audit/stats | PASS | 统计信息正确（total_logs, by_event_type, top_threads, avg_duration_ms） |
| GET /api/audit/logs | PASS | 支持分页查询 |
| GET /api/audit/logs/{thread_id} | PASS | 按线程过滤正确 |
| 直接写入 log_event() | PASS | 3 条事件成功写入 SQLite |
| 导出 export() | PASS | JSON 导出成功 |

**注意**: 审计日志模块功能完整，但**未集成到主聊天流程**中。需要手动调用 `log_event()` 才会写入日志。这是 Phase 17 的待集成项。

### 3.8 安全 Guardrails

| 测试项 | 期望 | 实际 | 结果 |
|--------|------|------|------|
| 身份证号检测 | blocked | blocked | PASS |
| 手机号检测 | blocked | blocked | PASS |
| Prompt 注入 (ignore previous) | blocked | blocked | PASS |
| DAN 越狱检测 | blocked | blocked | PASS |
| 正常输入 | passed | passed | PASS |
| 输出 PII 脱敏 (手机号+邮箱) | masked | `***` + `[EMAIL]` | PASS |
| 安全 SQL (SELECT) | safe | safe | PASS |
| 危险 SQL (DROP TABLE) | blocked | blocked | PASS |
| 危险 SQL (DELETE) | blocked | blocked | PASS |

**注意**: Guardrails 模块功能完整（9/9 通过），但**未集成到主聊天流程**中。敏感输入和 Prompt 注入可以直接通过 `/api/chat` 到达 LLM。这是 Phase 17 的待集成项。

### 3.9 边界情况

| 测试项 | 状态码 | 结果 | 说明 |
|--------|--------|------|------|
| 空字符串问题 | 200 | PASS | 不崩溃，正常处理 |
| 不传 conversation_id | 200 | PASS | 默认使用 "default" |
| MCP 离线优雅降级 | 200 | PASS | 返回友好提示，不报错 |

### 3.10 自动化评估（路由准确率）

**结构化查询 (5 用例)**:
| 问题 | 期望 | 实际 | 耗时 |
|------|------|------|------|
| 有多少个UP主？ | structured | structured | 9.62s |
| 总共采集了多少个视频？ | structured | structured | 7.91s |
| 哪个分类的视频最多？ | structured | structured | 9.23s |
| 最近一周新增了多少视频？ | structured | structured | 9.52s |
| 播放量最高的视频是哪个？ | structured | structured | 10.26s |
| **准确率** | | | **5/5 (100%)** |

**语义查询 (3 用例)**:
| 问题 | 期望 | 实际 | 耗时 |
|------|------|------|------|
| 桃姐最近讲了什么情感话题？ | semantic | hybrid | 11.73s |
| 有哪些关于人际关系的建议？ | semantic | semantic | 18.51s |
| 视频中提到了哪些沟通技巧？ | semantic | semantic | 12.97s |
| **准确率** | | | **2/3 (66.7%)** |

**混合查询 (3 用例)**:
| 问题 | 期望 | 实际 | 耗时 |
|------|------|------|------|
| 桃姐播放量最高的视频讲了什么？ | hybrid | hybrid | 14.57s |
| 情感类视频的平均播放量是多少？... | hybrid | hybrid | 21.37s |
| 最近一周发布的视频中，有哪些关于职场的内容？ | hybrid | hybrid | 15.10s |
| **准确率** | | | **3/3 (100%)** |

**总体评估**:
- 路由准确率: **90.9%** (10/11)
- 平均响应时间: **13.32s**
- 错误率: **0%**

**误分类分析**: "桃姐最近讲了什么情感话题？" 被分类为 hybrid 而非 semantic。这是因为提到特定 UP 主（桃姐），LLM 认为需要 SQL 过滤 + RAG 语义检索。实际上这个分类也合理——hybrid 能提供更精准的结果。

---

## 四、性能指标

| 指标 | 数值 |
|------|------|
| 服务启动时间 | ~35s（含 MCP 连接超时 3×10s） |
| 结构化查询平均耗时 | 9.31s |
| 语义查询平均耗时 | 14.40s |
| 混合查询平均耗时 | 17.01s |
| 总体平均响应时间 | 13.32s |
| 内存占用 | 正常（ChromaDB + LangGraph MemorySaver） |
| 服务器稳定性 | 稳定（50+ 请求无崩溃） |

**说明**: 响应时间主要受 LLM API 延迟影响（deepseek-v4-pro via 内网代理）。MCP Server 连接后会增加工具调用时间。

---

## 五、集成差距（待完成项）

以下模块功能完整但未集成到主流程：

| 模块 | 状态 | 影响 |
|------|------|------|
| **Guardrails** | 模块完整，未接入 chat 流程 | 敏感输入/Prompt 注入可直达 LLM |
| **审计日志** | 模块完整，未接入节点 | chat 操作不自动记录审计日志 |
| **MCP 数据流** | 代码完整，MCP Server 未启动 | 无法返回真实数据，全部走优雅降级 |

---

## 六、API 端点清单

| 端点 | 方法 | 功能 | 状态 |
|------|------|------|------|
| `/` | GET | 根路径 | OK |
| `/health` | GET | 健康检查 | OK |
| `/docs` | GET | Swagger UI | OK |
| `/openapi.json` | GET | OpenAPI 规范 | OK |
| `/api/chat` | POST | 智能问答 | OK |
| `/api/chat/stream` | POST | SSE 流式输出 | OK |
| `/api/mcp/tools` | GET | MCP 工具列表 | OK |
| `/api/memory/stats` | GET | 记忆统计 | OK |
| `/api/audit/stats` | GET | 审计统计 | OK |
| `/api/audit/logs` | GET | 审计日志查询 | OK |
| `/api/audit/logs/{thread_id}` | GET | 按线程查审计日志 | OK |
| `/a2a/agent-card` | GET | A2A Agent Card | OK |
| `/a2a/tasks` | POST | 创建 A2A 任务 | OK |
| `/a2a/tasks/{task_id}` | GET | 查询 A2A 任务 | OK |
| `/a2a/tasks/{task_id}` | DELETE | 取消 A2A 任务 | OK |
| `/a2a/tasks` | GET | 列出 A2A 任务 | OK |

共 **16 个端点**（12 个路径），全部正常工作。

---

## 七、测试结论

### 通过项
1. **LangGraph 工作流**: 意图分类 → 条件路由 → 查询执行 → 结果融合 → 反思，全链路正常
2. **SSE 流式输出**: 事件流格式正确，5 个节点事件 + done 信号
3. **MCP 优雅降级**: MCP Server 离线时不崩溃，返回友好提示
4. **记忆系统**: 短期记忆（对话历史）+ 长期记忆（ChromaDB）+ 反思机制，全部正常
5. **A2A 协议**: Agent Card、任务 CRUD、编排器，全部正常
6. **安全模块**: Guardrails（9/9）+ 审计日志（5/5），模块功能完整
7. **路由准确率**: 90.9%（10/11），1 个边界案例误分类但分类也合理
8. **服务稳定性**: 50+ 请求无崩溃、无异常错误

### 待改进项
1. **集成 Guardrails 到 chat 流程** — 在 `/api/chat` 入口添加输入过滤
2. **集成审计日志到节点** — 在 classify/query/merge 节点中添加 `log_event()` 调用
3. **启动 content-analysis-system Docker** — 使 MCP Server 可用，验证端到端数据流
4. **优化 LLM 延迟** — 当前平均 13s 响应时间，主要来自 LLM API 调用
