from __future__ import annotations

from pydantic import BaseModel


class IngestResult(BaseModel):
    doc_id: str
    title: str
    chunk_count: int
    collection: str
