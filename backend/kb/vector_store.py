from __future__ import annotations

from urllib.parse import urlparse

import chromadb
from chromadb import HttpClient
from chromadb.api.models.Collection import Collection

from config import Settings, get_settings
from kb.chunking import TextChunk
from kb.schemas import RetrievedChunk


def create_chroma_client(settings: Settings | None = None) -> HttpClient:
    settings = settings or get_settings()
    if not settings.chroma_url.strip():
        raise ValueError("CHROMA_URL is required")

    parsed = urlparse(settings.chroma_url.strip())
    if not parsed.scheme or not parsed.hostname:
        raise ValueError(f"Invalid CHROMA_URL: {settings.chroma_url!r}")

    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"CHROMA_URL scheme must be http or https, got {parsed.scheme!r}")

    port = parsed.port
    if port is None:
        port = 443 if parsed.scheme == "https" else 80

    kwargs: dict = {
        "host": parsed.hostname,
        "port": port,
        "ssl": parsed.scheme == "https",
    }
    if settings.chroma_auth_token:
        kwargs["headers"] = {"Authorization": f"Bearer {settings.chroma_auth_token}"}

    return chromadb.HttpClient(**kwargs)


class VectorStore:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._client = create_chroma_client(self._settings)
        self._collection: Collection = self._client.get_or_create_collection(
            name=self._settings.chroma_collection,
            metadata={"hnsw:space": "cosine"},
        )

    @property
    def chroma_url(self) -> str:
        return self._settings.chroma_url

    @property
    def collection_name(self) -> str:
        return self._settings.chroma_collection

    @property
    def count(self) -> int:
        return self._collection.count()

    def delete_by_doc_id(self, doc_id: str) -> None:
        existing = self._collection.get(where={"doc_id": doc_id})
        if existing["ids"]:
            self._collection.delete(ids=existing["ids"])

    def upsert_chunks(
        self,
        *,
        doc_id: str,
        title: str,
        doc_type: str,
        chunks: list[TextChunk],
        embeddings: list[list[float]],
    ) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings length mismatch")

        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict[str, str | int]] = []

        for chunk, _emb in zip(chunks, embeddings):
            ids.append(f"{doc_id}_{chunk.index}")
            documents.append(chunk.text)
            metadatas.append(
                {
                    "doc_id": doc_id,
                    "title": title,
                    "section": chunk.section,
                    "chunk_index": chunk.index,
                    "doc_type": doc_type,
                }
            )

        self._collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

    def similarity_search(
        self,
        query_embedding: list[float],
        *,
        k: int = 30,
        where: dict[str, str | int] | None = None,
    ) -> list[RetrievedChunk]:
        total = self._collection.count()
        if total == 0:
            return []

        n = min(k, total)
        kwargs: dict = {
            "query_embeddings": [query_embedding],
            "n_results": n,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where

        raw = self._collection.query(**kwargs)
        ids = raw.get("ids") or [[]]
        documents = raw.get("documents") or [[]]
        metadatas = raw.get("metadatas") or [[]]
        distances = raw.get("distances") or [[]]

        results: list[RetrievedChunk] = []
        for i, doc_id in enumerate(ids[0]):
            text = documents[0][i] if i < len(documents[0]) else ""
            meta = metadatas[0][i] if i < len(metadatas[0]) else {}
            dist = distances[0][i] if i < len(distances[0]) else None
            if not text:
                continue
            results.append(
                RetrievedChunk(
                    id=str(doc_id),
                    text=str(text),
                    metadata=dict(meta or {}),
                    distance=float(dist) if dist is not None else None,
                )
            )
        return results
