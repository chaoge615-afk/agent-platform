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
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入 API 密钥
```

### 3. 启动服务

```bash
python -m src.main
```

API 文档：http://localhost:8001/docs

## 项目结构

```
agent-platform/
├── src/
│   ├── agent/              # LangGraph Agent
│   │   ├── graph.py        # 工作流定义
│   │   ├── state.py        # 状态 Schema
│   │   └── nodes.py        # 节点函数
│   ├── mcp_client/         # MCP Client
│   │   └── manager.py      # Server 管理
│   ├── memory/             # 记忆系统
│   │   └── store.py        # 记忆存储
│   └── main.py             # FastAPI 入口
├── mcp_servers/            # MCP Server 配置
│   └── config.json         # Server 注册表
├── tests/                  # 测试
└── README.md
```

## 开发计划

### Phase 12: LangGraph 重构（第 1-2 周）
- [ ] LangGraph 核心概念学习（State、Node、Edge）
- [ ] 实现意图分类节点
- [ ] 实现条件路由
- [ ] 流式输出（SSE）
- [ ] Checkpoint 持久化

### Phase 13: MCP 集成（第 3-4 周）
- [ ] MCP Client 实现
- [ ] 连接 content-analysis-system 的 MCP Server
- [ ] 工具发现与注册

### Phase 14: 记忆系统（第 5-6 周）
- [ ] 短期记忆（对话上下文）
- [ ] 长期记忆（ChromaDB）
- [ ] 反思机制

## 与 content-analysis-system 的关系

| 项目 | 定位 | 技术栈 | 状态 |
|------|------|--------|------|
| content-analysis-system | 数据基础设施 | Multi-Agent Pipeline, FastAPI | 生产运行 |
| agent-platform | Agent 能力平台 | LangGraph, MCP, Memory | 开发中 |

两个项目通过 MCP 协议通信，代码完全独立。

## 许可证

MIT
