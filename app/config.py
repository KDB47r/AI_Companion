from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables or .env."""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AI Companion"
    dev_token: str = "dev-token"

    database_url: str = (
        "postgresql+asyncpg://postgres:ai_companion@127.0.0.1:5432/ai_companion"
    )
    db_echo: bool = False
    dev_user_external_id: str = "dev-user"

    # P2 context budget + rolling summary
    context_window_tokens: int = 32768
    summary_enabled: bool = True
    summary_trigger_ratio: float = 0.7
    summary_keep_recent_messages: int = 6
    summary_max_tokens: int = 512
    summary_model: str = "qwen-turbo"
    summary_temperature: float = 0.2
    summary_sync: bool = False
    token_safety_margin: float = 1.15

    # P3 tools / MCP
    tools_enabled: bool = True
    max_tool_steps: int = 5
    tool_timeout_seconds: float = 10.0
    tool_parallel_limit: int = 4
    max_tool_result_tokens: int = 2000
    tool_permission_mode: str = "readonly_auto"
    mcp_config_path: str = "config/mcp_servers.json"

    # P4.1 long-term memory
    memory_enabled: bool = True
    embedding_model: str = "text-embedding-v3"
    embedding_dimensions: int = 1024
    embedding_timeout_seconds: float = 20.0
    memory_top_k: int = 5
    memory_min_similarity: float = 0.35
    memory_max_tokens: int = 600
    memory_extract_every_turns: int = 3
    memory_extraction_model: str = "qwen-turbo"
    memory_extraction_temperature: float = 0.1
    memory_extraction_max_messages: int = 6
    memory_min_confidence: float = 0.6
    memory_max_content_chars: int = 500
    memory_dedupe_similarity: float = 0.9
    memory_sync: bool = False

    # P4.2 document RAG
    rag_enabled: bool = True
    rag_top_k: int = 5
    rag_min_similarity: float = 0.35
    rag_max_tokens: int = 1200
    rag_chunk_tokens: int = 500
    rag_chunk_overlap: int = 50
    rag_max_file_bytes: int = 2_000_000
    rag_max_chunks: int = 100
    rag_embedding_batch_size: int = 10

    llm_provider: str = "fake"
    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_api_key: str = ""
    llm_model: str = "deepseek-chat"
    llm_timeout_seconds: float = 120.0
    llm_max_tokens: int = 1024
    llm_temperature: float = 0.7
    llm_include_usage: bool = True

    fake_response: str = "你好呀，我是小火。今天想聊点什么？"
    fake_delay_seconds: float = 0.02

    sse_heartbeat_seconds: float = 15.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
