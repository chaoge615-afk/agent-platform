# Agent Platform - 项目约束

## 项目概述
通用 Agent 开发平台 — LangGraph 工作流 + MCP 协议 + 记忆系统，通过 MCP 调用 content-analysis-system 的能力

## 当前状态（2026-06-15）
- Phase 12-14: 全部完成 ✅
  - [x] LangGraph 核心实现（State、Node、Edge、条件路由）
  - [x] 流式输出（SSE）+ Checkpoint 持久化
  - [x] MCP Client（SSE 传输，优雅降级）
  - [x] 记忆系统（短期 + ChromaDB 长期 + 反思）
  - [x] MCP Server 包装层（content-analysis-system 侧，全链路打通）
  - [ ] 联调 content-analysis-system Docker 环境（待部署）
  - [ ] LangSmith 可观测性

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
│   ├── agent/          # LangGraph Agent
│   ├── mcp_client/     # MCP Client
│   ├── memory/         # 记忆系统
│   └── main.py         # FastAPI 入口
├── mcp_servers/        # MCP Server 配置
└── tests/              # 测试
```

## 与 content-analysis-system 的关系
- 本项目是 Agent 能力平台（LangGraph + MCP + Memory）
- content-analysis-system 是数据基础设施（通过 MCP Server 暴露能力）
- 两个项目通过 MCP 协议通信，代码完全独立

## 新会话启动流程
1. 读取 `README.md` 了解项目定位
2. 读取 `docs/` 下的开发文档（如有）
3. 检查 `.env` 配置
4. 继续开发
