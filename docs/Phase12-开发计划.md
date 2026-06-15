# Phase 12: LangGraph 深化开发计划

> 目标：将 agent-platform 从基础骨架升级为生产级 LangGraph Agent  
> 预计工期：2-3 天（AI 驱动）  
> 创建时间：2026-06-15

---

## 📋 总体目标

实现 LangGraph 的三大核心能力：
1. **多轮对话记忆** - Checkpoint 持久化，支持上下文保持
2. **流式输出** - SSE 实时推送处理阶段和文本
3. **人工干预** - Human-in-the-Loop，支持危险操作确认

---

## ✅ 已完成任务

### Day 1 上午：Checkpoint 持久化（已完成）

**任务清单：**
- [x] 实现 `CheckpointManager` 类（SQLite 存储）
- [x] 集成 `langgraph-checkpoint-sqlite`
- [x] 修改 `graph.py` 支持 checkpointer 参数
- [x] 修改 `main.py` 支持 conversation_id → thread_id
- [x] 新增 `GET /api/threads` 端点（列出所有对话线程）
- [x] 新增 `GET /api/threads/{id}/history` 端点（获取对话历史）
- [x] 编写 `test_multiturn.py` 多轮对话测试
- [x] 添加 `langgraph-checkpoint-sqlite` 依赖

**验证标准：**
- [x] 连续对话测试：3 轮对话正常
- [x] Checkpoint 数据持久化到 SQLite
- [x] 重启服务后对话历史不丢失

---

## 🎯 待完成任务

### Day 1 下午：SSE 流式输出（预计 1 小时）

**目标：** 实时推送处理阶段和文本，提升用户体验

**任务清单：**
- [ ] 新增 `POST /api/chat_stream` 端点（Server-Sent Events）
- [ ] 实现 5 阶段事件推送：
  - `classifying` - 分析意图
  - `routing` - 路由决策
  - `querying` - 查询数据
  - `answering` - 流式生成答案
  - `done` - 完成
- [ ] 修改节点函数支持事件追踪（`astream_events`）
- [ ] 编写 `tests/test_streaming.py` SSE 测试脚本
- [ ] 验证 SSE 事件推送正常

**验证标准：**
- [ ] `curl -N http://localhost:8001/api/chat_stream` 实时看到 SSE 事件
- [ ] 5 个阶段事件正确推送
- [ ] Token 流式输出（每 50-100ms 一个 token）

---

### Day 2 上午：Human-in-the-Loop（预计 1.5 小时）

**目标：** SQL 执行前可选人工确认，防止危险操作

**任务清单：**
- [ ] 修改 `query_sql` 节点支持中断（`langgraph.types.interrupt`）
- [ ] 实现危险 SQL 自动检测（DELETE/UPDATE/DROP/TRUNCATE）
- [ ] 新增 `POST /api/chat/resume` 端点（恢复中断的对话）
- [ ] 实现 `ResumeRequest` 数据模型（execute/modify/cancel）
- [ ] 编写 HITL 测试用例
- [ ] 验证 interrupt/resume 流程正常

**验证标准：**
- [ ] 危险 SQL（DELETE/UPDATE）自动触发 HITL
- [ ] `/api/chat/resume` 能正确恢复中断的工作流
- [ ] 取消操作正常处理
- [ ] 修改 SQL 后能正确执行

---

### Day 2 下午：前端改造（预计 2 小时）

**目标：** 对接 SSE，显示流式文本和处理进度

**任务清单：**
- [ ] 创建前端项目结构（React + TypeScript + Vite）
- [ ] 实现 `ChatWindow` 组件（主聊天窗口）
- [ ] 实现 `StageIndicator` 组件（阶段指示器）
- [ ] 实现 `HITLDialog` 组件（HITL 对话框）
- [ ] 实现 `MessageList` 组件（消息列表）
- [ ] 对接 SSE 流式输出（`fetch` + `ReadableStream`）
- [ ] 实现流式文本显示（带光标动画）
- [ ] 实现 HITL 确认对话框
- [ ] 测试前端交互正常

**验证标准：**
- [ ] 前端能接收 SSE 事件
- [ ] 阶段指示器实时更新（5 个阶段）
- [ ] 流式文本平滑显示（无闪烁）
- [ ] HITL 对话框正常弹出和响应
- [ ] 多轮对话正常工作

---

### Day 3 上午：评估体系（预计 2 小时）

**目标：** 建立自动化评估，量化 Agent 性能

**任务清单：**
- [ ] 生成 30+ 测试用例（结构化/语义/混合查询）
- [ ] 实现 `AgentEvaluator` 类（自动评估）
- [ ] 评估意图分类准确率
- [ ] 生成评估报告（JSON + 控制台输出）
- [ ] 实现基准测试脚本（响应时间、Token 消耗）
- [ ] 识别分类失败案例
- [ ] 优化 Prompt（提升准确率）

**验证标准：**
- [ ] 评估脚本能自动运行
- [ ] 生成 JSON 格式评估报告
- [ ] 准确率 ≥ 90%
- [ ] 识别出分类失败的案例（用于优化 Prompt）

---

### Day 3 下午：对比测试 + 文档（预计 1.5 小时）

**目标：** 对比新旧 Router，输出技术文章

**任务清单：**
- [ ] 实现对比测试脚本（新 Router vs 旧 Router 历史数据）
- [ ] 运行 50+ 测试用例对比
- [ ] 生成对比报告（准确率、延迟、Token 消耗）
- [ ] 编写技术对比文档（LangGraph vs Multi-Agent Pipeline）
- [ ] 撰写 CSDN 文章：《从 Multi-Agent Pipeline 到 LangGraph：Router Agent 重构实战》
  - 架构对比
  - 核心实现（Checkpoint + SSE + HITL）
  - 性能对比数据
  - 踩坑记录
  - 代码示例
- [ ] 发布 CSDN 文章
- [ ] GitHub Release v12.0

**验证标准：**
- [ ] 对比测试完成（50+ 测试用例）
- [ ] 生成对比报告（准确率、延迟、Token）
- [ ] CSDN 文章发布（≥ 3000 字）
- [ ] GitHub Release 创建

---

## 📊 任务总览

| 任务 | 状态 | 预计耗时 | 文件变更 | 验证标准 |
|------|------|---------|---------|---------|
| Checkpoint 持久化 | ✅ 已完成 | 2h | 4 文件 | 多轮对话测试 |
| SSE 流式输出 | ⏳ 待完成 | 1h | 3 文件 | SSE 事件测试 |
| Human-in-the-Loop | ⏳ 待完成 | 1.5h | 3 文件 | interrupt/resume 测试 |
| 前端改造 | ⏳ 待完成 | 2h | 5 文件 | UI 交互测试 |
| 评估体系 | ⏳ 待完成 | 2h | 4 文件 | 准确率 ≥ 90% |
| 对比测试 + 文档 | ⏳ 待完成 | 1.5h | 3 文件 | CSDN 文章发布 |

**总计：**
- **已完成**：1/6 任务（Checkpoint）
- **待完成**：5/6 任务
- **预计耗时**：8 小时（1-2 天）
- **新增文件**：22 个
- **代码行数**：约 2000 行
- **CSDN 文章**：1 篇

---

## 🚀 下一步行动

**立即开始 Day 1 下午任务：SSE 流式输出**

1. 修改 `src/main.py` 添加 `/api/chat_stream` 端点
2. 修改 `src/agent/nodes.py` 支持事件追踪
3. 新建 `tests/test_streaming.py` 测试脚本
4. 验证 SSE 事件推送正常

准备好开始了吗？🎯
