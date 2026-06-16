"""配置加载"""
import os
from typing import Literal
from dotenv import load_dotenv

load_dotenv()


class Config:
    # ==================== LLM API 配置 ====================

    # LLM 提供者选择
    LLM_PROVIDER: Literal["anthropic", "openai"] = os.getenv("LLM_PROVIDER", "anthropic")

    # Anthropic 兼容接口（Anthropic / MiniMax / 其他）
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_BASE_URL: str = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

    # OpenAI 兼容接口（OpenAI / DeepSeek / MiniMax / 其他）
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")

    # ==================== MCP Server 地址 ====================
    BILIBILI_MCP_URL: str = os.getenv("BILIBILI_MCP_URL", "http://localhost:9001/sse")
    RAG_MCP_URL: str = os.getenv("RAG_MCP_URL", "http://localhost:9002/sse")
    SQL_MCP_URL: str = os.getenv("SQL_MCP_URL", "http://localhost:9003/sse")

    # ==================== 记忆系统 ====================
    CHROMA_DATA_PATH: str = os.getenv("CHROMA_DATA_PATH", "./data/chroma_db")
    MEMORY_COLLECTION: str = os.getenv("MEMORY_COLLECTION", "agent_memory")

    # ==================== LangSmith 可观测性 ====================
    LANGCHAIN_TRACING_V2: bool = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
    LANGCHAIN_API_KEY: str = os.getenv("LANGCHAIN_API_KEY", "")
    LANGCHAIN_PROJECT: str = os.getenv("LANGCHAIN_PROJECT", "agent-platform")
    LANGCHAIN_ENDPOINT: str = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")

    # ==================== 服务配置 ====================
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8001"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
