# Agent Platform - 项目约束

## 项目概述
通用 Agent 开发平台 — LangGraph 工作流 + MCP 协议 + 记忆系统，通过 MCP 调用 content-analysis-system 的能力

## 当前状态（2026-06-15）
- **Phase 12: LangGraph 深化**（进行中，预计 2-3 天完成）
  - [x] 项目骨架搭建
  - [x] LangGraph 核心工作流（意图分类 → 路由 → 查询 → 融合）
  - [x] LLM API 调用（自定义 X-Api-Key 头，支持 thinking 模型）
  - [x] Checkpoint 持久化（SQLite，多轮对话支持）
  - [ ] SSE 流式输出（`/api/chat_stream` 端点）
  - [ ] Human-in-the-Loop（SQL 执行前确认）
  - [ ] 前端改造（React + SSE 对接）
  - [ ] 评估体系（100+ 测试用例）
  - [ ] 对比测试 + CSDN 文章
- **后续计划**：见 `docs/Phase13-20-开发计划总览.md`

## 技术栈
- Python 3.11+
- LangGraph + LangChain
- MCP Protocol (mcp SDK)
- FastAPI
- ChromaDB（记忆系统）
- LangSmith（可观测性，计划中）

## 开发规范

### 环境配置
- **Python 依赖必须使用国内镜像源**：
  ```bash
  pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
  ```
- 或使用清华镜像配置 `pip.conf`：
  ```ini
  [global]
  index-url = https://pypi.tuna.tsinghua.edu.cn/simple
  trusted-host = pypi.tuna.tsinghua.edu.cn
  ```

### 代码规范
- Git 提交用中文
- 环境变量走 `.env`，不硬编码
- API 密钥走环境变量，不提交到 Git
- 每个 Phase 完成后更新 `README.md` 的开发计划

### 项目结构
```
agent-platform/
├── src/
│   ├── agent/              # LangGraph Agent
│   │   ├── graph.py        # 工作流定义
│   │   ├── nodes.py        # 节点函数（意图分类、路由、查询、融合）
│   │   ├── state.py        # 状态 Schema
│   │   └── checkpoint.py   # Checkpoint 持久化（SQLite）
│   ├── mcp_client/         # MCP Client
│   │   └── manager.py      # MCP Server 管理器
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

## 与 content-analysis-system 的关系
- 本项目是 Agent 能力平台（LangGraph + MCP + Memory）
- content-analysis-system 是数据基础设施（通过 MCP Server 暴露能力）
- 两个项目通过 MCP 协议通信，代码完全独立

## Windows 启动脚本
- **`restart.bat`** - 完整重启（停止 + 清缓存 + 启动 + 健康检查）
- **`start.bat`** - 启动服务
- **`stop.bat`** - 停止服务
- 脚本调用 PowerShell，支持 UTF-8 输出

## 新会话启动流程
1. 读取 `README.md` 了解项目定位
2. 读取 `docs/Phase13-20-开发计划总览.md` 了解后续计划
3. 检查 `.env` 配置（LLM_PROVIDER、API_KEY、BASE_URL）
4. 运行 `restart.bat` 启动服务
5. 继续开发
