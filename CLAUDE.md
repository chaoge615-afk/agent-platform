# Agent Platform - 项目约束

## 项目概述
通用 Agent 开发平台 — LangGraph 工作流 + MCP 协议 + A2A 协议 + 记忆系统 + 安全治理，通过 MCP 调用 content-analysis-system 的能力

## 当前状态（2026-06-25）
- Phase 12-17: 全部完成 ✅
  - [x] LangGraph 核心实现（State、Node、Edge、条件路由）
  - [x] 流式输出（SSE）+ Checkpoint 持久化
  - [x] MCP Client（SSE 传输，优雅降级）
  - [x] 记忆系统（短期 + ChromaDB 长期 + 反思）
  - [x] MCP Server 包装层（content-analysis-system 侧，全链路打通）
  - [x] 评估体系（100+ 测试用例，100% 路由准确率）
  - [x] A2A 协议（Agent Card、Task、跨框架协作）
  - [x] 安全治理（Guardrails + 审计日志）
  - [x] K-01~K-12 问题修复（guardrails Luhn校验、AsyncSqliteSaver、OpenAI双provider、threads端点、Prompt增强）
  - [ ] 联调 content-analysis-system Docker 环境（待部署）
  - [ ] Phase 18-20: 企业平台实战 + Agent 开发平台

## 技术栈
- Python 3.11+
- LangGraph + LangChain
- MCP Protocol (mcp SDK)
- A2A Protocol (自定义实现)
- FastAPI
- ChromaDB（记忆系统）
- SQLite（审计日志、Checkpoint）
- LangSmith（可观测性，已配置）

## 项目结构

```
agent-platform/
├── src/
│   ├── agent/              # LangGraph Agent
│   │   ├── graph.py        # 工作流定义
│   │   ├── nodes.py        # 节点函数
│   │   ├── state.py        # 状态 Schema
│   │   └── checkpoint.py   # Checkpoint 持久化
│   ├── a2a/                # A2A 协议（Phase 16）
│   │   ├── protocol.py     # 协议定义（Agent Card、Task、Message）
│   │   ├── server.py       # A2A Server（暴露 Agent）
│   │   └── client.py       # A2A Client（调用其他 Agent）
│   ├── security/           # 安全治理（Phase 17）
│   │   ├── guardrails.py   # 输入/输出过滤
│   │   └── audit.py        # 审计日志（SQLite）
│   ├── mcp_client/         # MCP Client
│   │   └── manager.py      # MCP Server 管理器
│   ├── memory/             # 记忆系统
│   │   └── store.py        # 记忆存储（ChromaDB）
│   ├── config.py           # 配置管理
│   └── main.py             # FastAPI 入口
├── tests/                  # 测试套件（Phase 15）
│   ├── test_cases.py       # 100+ 测试用例
│   ├── evaluator.py        # 自动化评估
│   ├── benchmark.py        # 性能基准测试
│   ├── test_a2a.py         # A2A 协议测试
│   └── __main__.py         # 测试运行器
├── docs/                   # 开发文档
│   ├── Phase12-开发计划.md
│   ├── Phase13-20-开发计划总览.md
│   ├── 剩余开发计划.md
│   └── 开发进度总结.md
├── data/                   # 数据存储
│   ├── audit.db            # 审计日志（SQLite）
│   └── chroma_db/          # ChromaDB 向量数据
├── restart.bat             # Windows 重启脚本
├── start.bat               # Windows 启动脚本
├── stop.bat                # Windows 停止脚本
└── .env                    # 环境配置（不提交 Git）
```

## 开发规范

### 环境配置
- **Python 依赖必须使用国内镜像源**：
  ```bash
  pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
  ```

### 代码规范
- Git 提交用中文
- 环境变量走 `.env`，不硬编码
- API 密钥走环境变量，不提交到 Git
- 每个 Phase 完成后更新 `README.md` 的开发计划
- Windows 脚本使用 ASCII 标记（[OK] [FAIL]），避免 Unicode emoji

### 测试规范
- 每个 Phase 完成后必须测试
- 测试通过后才能推送 GitHub
- 评估报告保存在 `tests/evaluation_report.json`

## API 端点

### 核心 API
- `POST /api/chat` - 智能问答
- `POST /api/chat/stream` - SSE 流式输出
- `GET /api/threads` - 对话线程列表
- `GET /api/threads/{id}/history` - 对话历史
- `GET /health` - 健康检查

### MCP API
- `GET /api/mcp/tools` - MCP 工具列表

### 记忆 API
- `GET /api/memory/stats` - 记忆统计

### A2A API（Phase 16）
- `GET /a2a/agent-card` - 获取 Agent Card（能力声明）
- `POST /a2a/tasks` - 创建 A2A 任务
- `GET /a2a/tasks/{task_id}` - 获取任务状态
- `DELETE /a2a/tasks/{task_id}` - 取消任务
- `GET /a2a/tasks` - 列出所有任务

### 审计 API（Phase 17）
- `GET /api/audit/stats` - 审计统计
- `GET /api/audit/logs` - 查询审计日志
- `GET /api/audit/logs/{thread_id}` - 按线程查询

## 与 content-analysis-system 的关系
- 本项目是 Agent 能力平台（LangGraph + MCP + A2A + Memory + Security）
- content-analysis-system 是数据基础设施（通过 MCP Server 暴露能力）
- 两个项目通过 MCP 协议通信，代码完全独立

## Windows 启动脚本
- **`restart.bat`** - 完整重启（停止 + 清缓存 + 启动 + 健康检查）
- **`start.bat`** - 启动服务
- **`stop.bat`** - 停止服务

## 新会话启动流程
1. 读取 `README.md` 了解项目定位
2. 读取 `docs/开发进度总结.md` 了解当前状态
3. 检查 `.env` 配置（LLM_PROVIDER、API_KEY、BASE_URL）
4. 运行 `restart.bat` 启动服务
5. 继续开发

## 关键成就
- ✅ 100+ 测试用例（35 结构化 + 35 语义 + 30 混合）
- ✅ 100% 路由准确率（评估系统验证）
- ✅ A2A 协议实现（跨框架 Agent 协作）
- ✅ 安全治理（Guardrails + 审计日志）
- ✅ 可观测性（LangSmith 集成）
- ✅ 完整技术栈（LangGraph + MCP + A2A + 记忆 + 安全）

## 已知修复（2026-06-25）

### agent-platform
| 编号 | 修复内容 |
|------|---------|
| K-01 | call_llm_direct 支持 OpenAI 格式（双 provider 分支） |
| K-02 | 注册 GET /api/threads 和 GET /api/threads/{id}/history 端点 |
| K-03 | MemorySaver → AsyncSqliteSaver 持久化 checkpointer（lifespan 初始化） |
| K-04 | Guardrail PII 正则误报修复（Luhn 校验 + 边界约束 + 上下文关键词） |
| K-05 | SQL 查询链路增强 DEBUG 日志 |
| K-07 | Guardrail 拦截层级修正（行为护栏优先于 PII 检查） |
| K-09 | Guardrail 审计事件统一 severity + rule_type 字段 |
| K-12 | classify_intent Prompt 增加多轮对话上下文继承规则 |

### agent-platform（2026-06-26 遗留问题修复第二轮）
| 编号 | 修复内容 |
|------|---------|
| LG-09 | classify_intent INTENT_SYSTEM_PROMPT 收敛 hybrid 规则（须含结构化数字子句）+ 新增轻量后校验。仅改 prompt，不加全局 temperature（实测 temp=0 在该栈无效且污染 merge/反思），根因详见 [遗留问题修复方案.md](遗留问题修复方案.md) |
| K-15 | merge_results 改用 `_is_valid_result`（error 字段为主、关键词兜底，补「无可用工具」「服务不可用」），修复误把错误文本当有效答案 |
| K-16 | MCPManager 重连接入 list_tools 真实故障路径：每 server 独立 AsyncExitStack + asyncio.Lock 双检重连，单请求内自愈，/health 不再误报 connected=true。nodes.py `_call_mcp_tool` not _connected 时先重连 |
| MS-01 | get_thread_history 改读 writes 表，用 JsonPlusSerializer.loads_typed 解码 channel 值，显式 current_turn 按 turn 聚合，修复 question/route_type/final_answer 回填全空 |

### agent-studio
| 编号 | 修复内容 |
|------|---------|
| K-08 | 创建 Agent 模板 data:dict → Pydantic AgentTemplateCreate 模型（修复中文 UTF-8 解析） |

### content-analysis-system
| 编号 | 修复内容 |
|------|---------|
| K-06 | 清理可疑 hacked 表 |
| K-10 | ChromaDB v1→v2 确认无需修改（SDK 自动处理） |
| K-11 | text-to-sql 查询质量优化（UP主 LIKE 模糊匹配 + play_count 字段 + 时间 WHERE 过滤） |
