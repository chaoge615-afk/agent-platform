"""配置加载"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # LLM API
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # MCP Server 地址
    BILIBILI_MCP_URL: str = os.getenv("BILIBILI_MCP_URL", "http://localhost:9001")
    RAG_MCP_URL: str = os.getenv("RAG_MCP_URL", "http://localhost:9002")
    SQL_MCP_URL: str = os.getenv("SQL_MCP_URL", "http://localhost:9003")

    # 记忆系统
    CHROMA_HOST: str = os.getenv("CHROMA_HOST", "localhost")
    CHROMA_PORT: int = int(os.getenv("CHROMA_PORT", "8001"))
    MEMORY_COLLECTION: str = os.getenv("MEMORY_COLLECTION", "agent_memory")

    # 服务配置
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8001"))
