from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import TYPE_CHECKING

from config import Settings, get_settings

if TYPE_CHECKING:
    from langchain_community.embeddings import DashScopeEmbeddings


@lru_cache(maxsize=2)
def _embeddings_client(*, api_key: str, model: str) -> DashScopeEmbeddings:
    from langchain_community.embeddings import DashScopeEmbeddings

    return DashScopeEmbeddings(model=model, dashscope_api_key=api_key)


def get_embeddings(settings: Settings | None = None) -> DashScopeEmbeddings:
    settings = settings or get_settings()
    if not settings.dashscope_api_key:
        raise ValueError("DASHSCOPE_API_KEY is required for knowledge base embedding")
    return _embeddings_client(api_key=settings.dashscope_api_key, model=settings.embedding_model)


async def embed_texts(texts: list[str], *, settings: Settings | None = None) -> list[list[float]]:
    if not texts:
        return []
    client = get_embeddings(settings)

    def _run() -> list[list[float]]:
        return client.embed_documents(texts)

    return await asyncio.to_thread(_run)


async def embed_query(text: str, *, settings: Settings | None = None) -> list[float]:
    vectors = await embed_texts([text], settings=settings)
    if not vectors:
        raise ValueError("empty embedding for query")
    return vectors[0]
