# Agent Platform

> 通用 Agent 开发平台 — LangGraph 工作流 + MCP 协议 + 记忆系统

## 项目定位

这是一个**通用 Agent 平台**，通过 MCP 协议调用外部工具（如 content-analysis-system），实现智能问答。

```
agent-platform (本项目)              content-analysis-system (外部工具)
┌─────────────────┐                 ┌─────────────────────┐
│  LangGraph Agent │                 │  bilibili-mcp-server │
│  记忆系统        │  ← MCP协议 →   │  rag-mcp-server      │
│  MCP Client      │   (HTTP/stdio) │  sql-mcp-server      │
└─────────────────┘                 └─────────────────────┘
```

## 技术栈

- **LangGraph**: Agent 工作流编排（State、Node、Edge）
- **MCP Protocol**: 标准化工具调用协议
- **ChromaDB**: 记忆系统向量存储
- **FastAPI**: API 服务
- **LangSmith**: Agent 可观测性（计划中）

## 快速开始

### 1. 安装依赖

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入 LLM API 配置
```

**支持的 LLM 提供者：**
- **Anthropic 兼容接口**（Anthropic / MiniMax / 其他）
  - `LLM_PROVIDER=anthropic`
  - `ANTHROPIC_API_KEY`、`ANTHROPIC_BASE_URL`、`ANTHROPIC_MODEL`
- **OpenAI 兼容接口**（OpenAI / DeepSeek / MiniMax / 其他）
  - `LLM_PROVIDER=openai`
  - `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_MODEL`

### 3. 启动服务

**Windows（推荐）：**
```bash
# 双击或命令行运行
restart.bat    # 完整重启（停止 + 清缓存 + 启动 + 健康检查）
start.bat      # 启动服务
stop.bat       # 停止服务
```

**Linux/Mac：**
```bash
python -m src.main
```

**API 文档：** http://localhost:8001/docs

**健康检查：** http://localhost:8001/health

## 项目结构

```
agent-platform/
├── src/
│   ├── agent/              # LangGraph Agent
│   │   ├── graph.py        # 工作流定义
│   │   ├── nodes.py        # 节点函数（意图分类、路由、查询、融合）
│   │   ├── state.py        # 状态 Schema
│   │   └── checkpoint.py   # Checkpoint 持久化（SQLite）
│   ├── mcp_client/         # MCP Client
│   │   └── manager.py      # Server 管理器
│   ├── memory/             # 记忆系统
│   │   └── store.py        # 记忆存储
│   ├── config.py           # 配置管理
│   └── main.py             # FastAPI 入口
├── tests/                  # 测试
│   ├── test_api.py         # API 测试
│   ├── test_multiturn.py   # 多轮对话测试
│   └── test_direct.py      # 直接函数测试
├── docs/                   # 开发文档
│   └── Phase13-20-开发计划总览.md
├── data/                   # 数据存储
│   └── checkpoints.db      # Checkpoint SQLite 数据库
├── restart.bat             # Windows 重启脚本
├── start.bat               # Windows 启动脚本
├── stop.bat                # Windows 停止脚本
└── .env                    # 环境配置（不提交 Git）
```

## 开发计划

### Phase 12: LangGraph 深化（第 1-2 周）🔄 进行中

**已完成：**
- [x] LangGraph 核心工作流（意图分类 → 路由 → 查询 → 融合）
- [x] 意图分类节点（支持 structured/semantic/hybrid）
- [x] 条件路由
- [x] LLM API 调用（自定义 X-Api-Key 头，支持 thinking 模型）
- [x] Checkpoint 持久化（SQLite，多轮对话支持）

**进行中：**
- [ ] SSE 流式输出（`/api/chat_stream` 端点）
- [ ] Human-in-the-Loop（SQL 执行前确认）
- [ ] 前端改造（React + SSE 对接）
- [ ] 评估体系（100+ 测试用例）
- [ ] 对比测试 + CSDN 文章

### Phase 13-20: 后续计划

详见 `docs/Phase13-20-开发计划总览.md`

**主要阶段：**
- **Phase 13**: MCP Server 集成（3 个 MCP Server + MCP Client）
- **Phase 14**: Agent 记忆系统（短期/长期/情景记忆 + 反思机制）
- **Phase 15**: Agent 可观测性（LangSmith + 评估体系）
- **Phase 16**: A2A 协议（跨框架 Agent 协作）
- **Phase 17**: 安全与企业级（Guardrails + HITL + 审计日志）
- **Phase 18**: 企业平台实战（Dify/Coze/百炼）
- **Phase 19-20**: 综合项目（Agent 开发平台 - 面试杀手锏）

## 当前功能

### ✅ 已实现

**LangGraph 工作流**
- 意图分类（structured / semantic / hybrid）
- 条件路由（根据意图分发到 SQL/RAG/混合查询）
- 多轮对话支持（Checkpoint 持久化）

**LLM API 调用**
- 支持 Anthropic 兼容接口（Anthropic / MiniMax / 其他）
- 支持 OpenAI 兼容接口（OpenAI / DeepSeek / MiniMax / 其他）
- 自定义 X-Api-Key 请求头（适配内网代理）
- 支持 thinking 模型（自动跳过 thinking 块，提取 text 块）
- 自动去除 LLM 返回的 markdown 代码块标记

**API 端点**
- `POST /api/chat` - 智能问答（支持 conversation_id 多轮对话）
- `GET /api/threads` - 列出所有对话线程
- `GET /api/threads/{id}/history` - 获取对话历史
- `GET /health` - 健康检查
- `GET /docs` - API 文档（Swagger UI）

**Windows 启动脚本**
- `restart.bat` - 完整重启（停止 + 清缓存 + 启动 + 健康检查）
- `start.bat` - 启动服务
- `stop.bat` - 停止服务

### ⏳ 计划中

- SSE 流式输出（实时推送处理阶段和文本）
- Human-in-the-Loop（SQL 执行前人工确认）
- MCP Server 集成（bilibili/rag/sql）
- 记忆系统（短期/长期/情景记忆 + 反思机制）
- 前端改造（React + SSE 对接）
- 评估体系（100+ 测试用例）

## 与 content-analysis-system 的关系

| 项目 | 定位 | 技术栈 | 状态 |
|------|------|--------|------|
| content-analysis-system | 数据基础设施 | Multi-Agent Pipeline, FastAPI | 生产运行 |
| agent-platform | Agent 能力平台 | LangGraph, MCP, Memory | 开发中 |

两个项目通过 MCP 协议通信，代码完全独立。

## 许可证

MIT
