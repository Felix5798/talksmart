"""Knowledge base: chunking, embedding, remote Chroma storage (ingest only)."""

from .ingest import ingest_markdown, ingest_markdown_file
from .schemas import IngestResult

__all__ = [
    "IngestResult",
    "ingest_markdown",
    "ingest_markdown_file",
]
