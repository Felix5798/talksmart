from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_ENV_FILE = _BACKEND_DIR / ".env"
_ENV_FILES = [str(_ENV_FILE)] if _ENV_FILE.is_file() else []


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILES or None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    dashscope_api_key: str | None = None
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "ecommerce_chatbot"
    database_url: str | None = None  # reserved for MySQL / SQLAlchemy

    llm_model: str = "qwen-turbo"
    max_dialog_turns: int = 5  # last N user+assistant rounds kept in context

    default_uid: str = "1001"

    # Commerce MCP (Streamable HTTP), separate process — see `run_mcp_http.py` (default port 8200).
    mcp_streamable_http_url: str = "http://127.0.0.1:8200/mcp"


@lru_cache
def get_settings() -> Settings:
    return Settings()
