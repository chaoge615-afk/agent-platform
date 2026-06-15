# Phase 13-20: 后续开发计划总览

> 创建时间：2026-06-15  
> 预计总工期：18-20 周（AI 驱动压缩为 3-4 周）

---

## 📋 Phase 13: MCP Server 集成（Week 3-4）

**目标：** 将 content-analysis-system 的能力封装为 MCP Server，供 agent-platform 调用

### 任务清单

#### Week 3: MCP Server 开发

**Day 1-2: bilibili-mcp-server**
- 创建 MCP Server 项目结构
- 实现 4 个 Tool：
  - `search_videos` - 搜索视频
  - `get_video_transcript` - 获取转写文本
  - `get_video_summary` - 获取精炼摘要
  - `trigger_collection` - 触发采集任务
- 实现 2 个 Resource：
  - `up_masters://list` - UP主列表
  - `categories://stats` - 分类统计
- 编写 Dockerfile 和文档
- 测试 MCP Server 启动和调用

**Day 3-4: rag-mcp-server**
- 创建 MCP Server 项目结构
- 实现 3 个 Tool：
  - `query_knowledge` - 语义检索知识库
  - `get_similar_videos` - 相似视频推荐
  - `get_category_videos` - 按分类查询
- 实现 1 个 Resource：
  - `knowledge://stats` - 知识库统计
- 编写 Dockerfile 和文档
- 测试 MCP Server 启动和调用

**Day 5: sql-mcp-server**
- 创建 MCP Server 项目结构
- 实现 2 个 Tool：
  - `execute_query` - 执行 SQL 查询
  - `get_table_schema` - 获取表结构
- 实现 SQL 安全检查（拦截 DELETE/UPDATE/DROP）
- 编写 Dockerfile 和文档
- 测试 MCP Server 启动和调用

#### Week 4: MCP Client 集成

**Day 1-2: MCP Client 管理器**
- 实现 `MCPManager` 类
- 支持连接多个 MCP Server（stdio 模式）
- 实现工具发现和注册
- 实现工具调用代理
- 连接 3 个 MCP Server 并验证

**Day 3: 节点函数改造**
- 修改 `query_sql` 节点：通过 MCP 调用 sql-mcp-server
- 修改 `query_rag` 节点：通过 MCP 调用 rag-mcp-server
- 修改 `merge_results` 节点：融合多 Server 结果
- 测试端到端调用链路

**Day 4-5: 跨 Server 查询**
- 实现混合查询：`"桃姐最近聊了什么情感话题？"`
  - bilibili-mcp 获取视频列表
  - rag-mcp 检索内容
  - 融合结果返回
- 编写集成测试
- 性能优化和错误处理
- 发布 CSDN 文章：《MCP 协议实战：把 B 站知识库封装为标准化工具》

### 交付物
- 3 个 MCP Server（bilibili/rag/sql）
- 9 个 MCP 工具
- 3 个 MCP 资源
- MCP Client 集成
- 1 篇 CSDN 文章

---

## 📋 Phase 14: Agent 记忆系统（Week 5-6）

**目标：** 实现短期/长期/情景记忆和反思机制，让 Agent 真正"记住"用户

### 任务清单

#### Week 5: 记忆存储实现

**Day 1-2: 短期记忆（对话上下文）**
- 扩展 LangGraph Checkpoint 功能
- 实现滑动窗口策略（保留最近 N 轮对话）
- 实现上下文压缩（超过 4K token 时自动摘要）
- 实现指代解析（"她" "那个UP主" → 具体名称）
- 测试多轮对话上下文保持

**Day 3-4: 长期记忆（用户偏好）**
- 创建 ChromaDB collection: `user_memory`
- 实现用户偏好自动记录：
  - 常问的 UP 主
  - 偏好的分类
  - 查询模式
- 实现语义检索（新问题 → 检索相似历史查询）
- 实现记忆合并和去重
- 测试长期记忆存储和检索

**Day 5: 情景记忆（关键事件）**
- 定义事件类型：
  - 首次查询某个 UP 主
  - SQL 生成失败重试
  - 发现新分类
- 实现事件触发器（模式匹配）
- 实现事件存储和检索
- 实现情景回放功能
- 测试情景记忆记录

#### Week 6: 反思机制 + 可视化

**Day 1-2: 反思机制**
- 实现 SQL 生成失败反思：
  - 分析错误原因
  - 调整 Prompt 策略
  - 记录反思日志
- 实现 RAG 检索无结果反思：
  - 检查过滤条件是否过严
  - 自动放宽重试
- 实现反思记录存储（ChromaDB）
- 测试反思机制触发和改进

**Day 3-4: 记忆可视化**
- 前端新增"记忆面板"
- 展示用户偏好词云
- 展示历史查询时间线
- 展示反思记录
- 实现记忆管理功能（查看/删除/导出）
- 测试可视化展示

**Day 5: 记忆管理策略**
- 实现遗忘机制（长期未使用的记忆降权）
- 实现记忆合并（相似记忆合并）
- 实现优先级排序（重要记忆优先）
- 实现记忆容量限制（超过阈值自动清理）
- 发布 CSDN 文章：《Agent 记忆系统设计：让 AI 助手真正"记住"你》

### 交付物
- 短期记忆（对话上下文管理）
- 长期记忆（用户偏好学习）
- 情景记忆（关键事件记录）
- 反思机制（自我改进）
- 记忆可视化面板
- 1 篇 CSDN 文章

---

## 📋 Phase 15: Agent 可观测性（Week 7-8）

**目标：** 集成 LangSmith，建立 Agent 评估和监控体系

### 任务清单

#### Week 7: LangSmith 集成

**Day 1-2: LangSmith 配置**
- 注册 LangSmith 账号
- 获取 API Key
- 配置环境变量
- 集成 LangChain 追踪
- 验证追踪数据上报

**Day 3-4: 调用链追踪**
- 追踪 LangGraph 工作流执行
- 追踪 LLM 调用（输入/输出/Token）
- 追踪 MCP 工具调用
- 追踪节点执行时间
- 在 LangSmith UI 查看追踪数据

**Day 5: Token 消耗监控**
- 统计每次查询的 Token 消耗
- 按节点分类统计
- 设置 Token 预算告警
- 实现成本优化建议

#### Week 8: 评估体系

**Day 1-2: 评估数据集**
- 构建 100+ 测试用例
- 标注 expected_route 和 filters
- 覆盖结构化/语义/混合查询
- 包含边界情况和失败案例

**Day 3-4: 自动化评估**
- 实现评估脚本
- 自动运行评估（准确率/延迟/Token）
- 生成评估报告（JSON + HTML）
- 识别分类失败案例
- 优化 Prompt（提升准确率）

**Day 5: A/B 测试 + 仪表盘**
- 实现不同 Prompt 策略对比
- 实现成本监控仪表盘
- 展示查询类型分布
- 展示响应时间分布
- 发布 CSDN 文章：《Agent 可观测性实战：用 LangSmith 监控你的 AI 系统》

### 交付物
- LangSmith 集成
- 100+ 测试用例
- 自动化评估脚本
- 成本监控仪表盘
- 1 篇 CSDN 文章

---

## 📋 Phase 16: A2A 协议 + 多 Agent 协作（Week 9-10）

**目标：** 实现跨框架 Agent 通信，支持 LangGraph Agent 调用 Multi-Agent Pipeline Agent

### 任务清单

#### Week 9: A2A Server 开发

**Day 1-2: A2A 协议学习**
- 学习 A2A 协议规范
- 理解 Agent Card、Task、Message、Artifact 概念
- 学习 A2A Python SDK
- 设计 Agent Card（能力声明）

**Day 3-4: Router Agent 暴露为 A2A Server**
- 实现 A2A Server 端点
- 注册 Agent Card（能力：问答、路由、融合）
- 实现 Task 创建和执行
- 实现 Message 和 Artifact 返回
- 测试 A2A Server 启动

**Day 5: A2A Client 集成**
- 实现 A2A Client
- 连接到其他 A2A Server
- 实现远程 Agent 调用
- 测试结果返回和解析

#### Week 10: 跨框架协作

**Day 1-2: 多 Agent 协作系统**
- LangGraph Agent 通过 A2A 调用 Multi-Agent Pipeline Agent
- 实现任务分配策略
- 实现结果融合
- 测试跨框架调用

**Day 3-4: Agent 能力注册表**
- 实现 Agent 能力声明
- 实现动态路由（根据能力分配任务）
- 实现负载均衡
- 测试能力匹配和路由

**Day 5: 文档和发布**
- 编写 A2A 协议使用文档
- 发布 CSDN 文章：《A2A 协议：让不同框架的 Agent 互相通信》

### 交付物
- A2A Server（Router Agent）
- A2A Client
- 跨框架协作系统
- Agent 能力注册表
- 1 篇 CSDN 文章

---

## 📋 Phase 17: Agent 安全与企业级实践（Week 11-12）

**目标：** 实现 Guardrails、HITL 和审计日志，确保 Agent 安全可靠

### 任务清单

#### Week 11: Guardrails + HITL

**Day 1-2: Guardrails（输入/输出过滤）**
- 实现输入过滤（敏感词检测、Prompt 注入防护）
- 实现输出过滤（个人信息脱敏、有害内容拦截）
- 实现行为边界设定（禁止执行危险操作）
- 测试 Guardrails 拦截效果

**Day 3-4: Human-in-the-Loop 增强**
- 扩展 HITL 到更多场景（不仅仅是 SQL）
- 实现自动/手动模式切换
- 实现 HITL 超时自动处理
- 实现 HITL 历史记录
- 测试 HITL 流程

**Day 5: 权限管理**
- 实现 Tool 调用权限分级
- 实现数据访问控制
- 实现用户角色管理
- 测试权限控制效果

#### Week 12: 审计日志 + 合规

**Day 1-2: 操作审计日志**
- 记录每次 Agent 决策的完整链路
- 记录 LLM 调用（输入/输出/Token）
- 记录 MCP 工具调用
- 记录 HITL 决策
- 实现日志查询和导出

**Day 3-4: 决策链路追溯**
- 实现决策可视化
- 支持按 thread_id 追溯
- 支持按时间范围查询
- 实现决策回放功能
- 测试追溯功能

**Day 5: 沙箱执行 + 文档**
- 实现代码执行沙箱（安全隔离）
- 编写安全治理文档
- 发布 CSDN 文章：《Agent 安全治理：从开发到生产的最后一道防线》

### 交付物
- Guardrails（输入/输出过滤）
- HITL 增强
- 权限管理系统
- 操作审计日志
- 决策链路追溯
- 1 篇 CSDN 文章

---

## 📋 Phase 18: 企业级 Agent 平台实战（Week 13-16）

**目标：** 在 Dify/Coze/百炼等平台实战，积累企业级开发经验

### 任务清单

#### Week 13-14: Dify 平台实战

**任务：**
- 学习 Dify 平台（工作流编排、知识库管理）
- 搭建保险行业 Agent（智能核保问答）
- 实现知识库导入和检索
- 实现工作流编排
- 实现 Agent 发布和部署
- 对比 Dify vs LangGraph 实现差异

#### Week 15-16: Coze + 百炼平台实战

**任务：**
- 学习 Coze 平台（Bot 开发、插件系统）
- 发布公开 Bot（情感咨询助手）
- 积累用户数据
- 学习阿里百炼平台
- 对比三大平台优劣

### 交付物
- Dify 保险行业 Agent
- Coze 公开 Bot
- 三大平台对比分析
- 1 篇 CSDN 文章：《三大 Agent 平台横向对比：LangGraph vs Dify vs Coze》

---

## 📋 Phase 19-20: 综合项目 — Agent 开发平台（Week 17-20）

**目标：** 整合 20 周所学，构建企业级 Agent 开发平台（面试杀手锏）

### 平台功能

```
┌─────────────────────────────────────────────┐
│              Agent 开发平台                    │
├──────────────┬──────────────────────────────┤
│  Agent 市场   │ 多个预置 Agent（SQL/RAG/...）  │
│  工作流编排   │ LangGraph 可视化编辑器          │
│  工具管理     │ MCP Server 注册与发现           │
│  记忆系统     │ 共享记忆 + Agent 私有记忆        │
│  可观测性     │ LangSmith 集成 + 自定义仪表盘    │
│  安全治理     │ Guardrails + HITL + 审计日志    │
│  部署运维     │ Docker Compose 一键部署         │
└──────────────┴──────────────────────────────┘
```

### 任务清单

**Week 17-18: 核心功能开发**
- Agent 市场（预置 Agent 管理）
- 工作流编排（LangGraph 可视化编辑器）
- 工具管理（MCP Server 注册与发现）

**Week 19-20: 高级功能 + 部署**
- 记忆系统（共享 + 私有）
- 可观测性（LangSmith 集成）
- 安全治理（Guardrails + HITL）
- Docker Compose 一键部署
- 编写完整文档
- 发布 CSDN 文章：《从零构建企业级 Agent 开发平台（面试杀手锏）》

### 交付物
- 完整的 Agent 开发平台
- 可视化工作流编辑器
- MCP Server 管理系统
- 完整的文档和教程
- 1 篇 CSDN 文章

---

## 📊 总体进度跟踪

| Phase | 名称 | 预计工期 | 状态 | CSDN 文章 |
|-------|------|---------|------|----------|
| 12 | LangGraph 深化 | 2-3 天 | 🔄 进行中 | 待发布 |
| 13 | MCP Server 集成 | 2-3 天 | ⏳ 待开始 | 待发布 |
| 14 | Agent 记忆系统 | 2-3 天 | ⏳ 待开始 | 待发布 |
| 15 | Agent 可观测性 | 2-3 天 | ⏳ 待开始 | 待发布 |
| 16 | A2A 协议 | 2-3 天 | ⏳ 待开始 | 待发布 |
| 17 | 安全与企业级 | 2-3 天 | ⏳ 待开始 | 待发布 |
| 18 | 企业平台实战 | 4-5 天 | ⏳ 待开始 | 待发布 |
| 19-20 | 综合项目 | 5-7 天 | ⏳ 待开始 | 待发布 |

**总计：**
- **预计总工期**：21-28 天（3-4 周，AI 驱动）
- **CSDN 文章**：8 篇
- **GitHub 项目**：2 个（content-analysis-system + agent-platform）
- **面试杀手锏**：Agent 开发平台

---

## 🎯 里程碑

| 时间点 | 里程碑 | 产出 |
|--------|--------|------|
| Week 2 | Phase 12 完成 | LangGraph Agent v1.0 + CSDN 文章 |
| Week 4 | Phase 13 完成 | 3 个 MCP Server + CSDN 文章 |
| Week 6 | Phase 14 完成 | 记忆系统 + CSDN 文章 |
| Week 8 | Phase 15 完成 | LangSmith 集成 + CSDN 文章 |
| Week 10 | Phase 16 完成 | A2A 协作系统 + CSDN 文章 |
| Week 12 | Phase 17 完成 | 安全治理 + CSDN 文章 |
| Week 16 | Phase 18 完成 | 企业平台实战 + CSDN 文章 |
| Week 20 | Phase 19-20 完成 | Agent 开发平台 + CSDN 文章 |

---

## 🚀 下一步行动

**立即完成 Phase 12 剩余任务：**
1. SSE 流式输出（1 小时）
2. Human-in-the-Loop（1.5 小时）
3. 前端改造（2 小时）
4. 评估体系（2 小时）
5. 对比测试 + 文档（1.5 小时）

**然后进入 Phase 13：MCP Server 集成**

准备好开始了吗？🎯
