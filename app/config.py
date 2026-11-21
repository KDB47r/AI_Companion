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
