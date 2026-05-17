"""Knowledge base: ingest, vector retrieval, and rerank for RAG."""

from .ingest import ingest_markdown, ingest_markdown_file
from .retrieval import format_kb_context, kb_system_prompt, retrieve_for_qa
from .schemas import IngestResult, RetrievedChunk

__all__ = [
    "IngestResult",
    "RetrievedChunk",
    "format_kb_context",
    "ingest_markdown",
    "ingest_markdown_file",
    "kb_system_prompt",
    "retrieve_for_qa",
]
