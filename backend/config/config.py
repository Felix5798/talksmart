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
    mongodb_uri: str
    mongodb_db: str
    database_url: str | None = None  # reserved for MySQL / SQLAlchemy

    llm_model: str = "qwen-turbo"
    max_dialog_turns: int = 5  # last N user+assistant rounds kept in context

    default_uid: str = "1001"

    # Commerce MCP (Streamable HTTP), separate process — see `run/run_mcp_http.py` (default port 8200).
    mcp_streamable_http_url: str = "http://127.0.0.1:8200/mcp"

    # Knowledge base (remote Chroma + DashScope embeddings)
    chroma_url: str
    chroma_auth_token: str | None = None
    chroma_collection: str = "kb_ecommerce_v1"
    embedding_model: str = "text-embedding-v3"
    kb_chunk_size: int = 500
    kb_chunk_overlap: int = 80
    kb_retrieval_top_k: int = 30
    kb_rerank_top_n: int = 5
    kb_rerank_min_score: float = 0.2
    rerank_model: str = "qwen3-rerank"
    kb_log_level: str = "INFO"  # DEBUG to see full chunk text in RAG logs


@lru_cache
def get_settings() -> Settings:
    return Settings()
