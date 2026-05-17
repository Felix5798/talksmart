from __future__ import annotations

from pathlib import Path

from config import Settings, get_settings
from kb.chunking import chunk_markdown
from kb.embeddings import embed_texts
from kb.schemas import IngestResult
from kb.vector_store import VectorStore


async def ingest_markdown(
    content: str,
    *,
    doc_id: str,
    title: str,
    doc_type: str = "policy",
    settings: Settings | None = None,
) -> IngestResult:
    """Chunk markdown, embed, and upsert into Chroma (replaces existing chunks for doc_id)."""
    settings = settings or get_settings()

    chunks = chunk_markdown(
        content,
        chunk_size=settings.kb_chunk_size,
        chunk_overlap=settings.kb_chunk_overlap,
    )
    if not chunks:
        raise ValueError("no chunks produced from document")

    texts = [c.text for c in chunks]
    embeddings = await embed_texts(texts, settings=settings)

    store = VectorStore(settings)
    store.delete_by_doc_id(doc_id)
    store.upsert_chunks(
        doc_id=doc_id,
        title=title,
        doc_type=doc_type,
        chunks=chunks,
        embeddings=embeddings,
    )

    return IngestResult(
        doc_id=doc_id,
        title=title,
        chunk_count=len(chunks),
        collection=store.collection_name,
    )


async def ingest_markdown_file(
    path: Path,
    *,
    doc_id: str | None = None,
    title: str | None = None,
    doc_type: str = "return_policy",
    settings: Settings | None = None,
) -> IngestResult:
    path = path.resolve()
    if not path.is_file():
        raise FileNotFoundError(path)

    content = path.read_text(encoding="utf-8")
    doc_id = doc_id or path.stem
    title = title or doc_id

    return await ingest_markdown(
        content,
        doc_id=doc_id,
        title=title,
        doc_type=doc_type,
        settings=settings,
    )
