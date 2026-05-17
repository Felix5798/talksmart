from __future__ import annotations

from pydantic import BaseModel, Field


class IngestResult(BaseModel):
    doc_id: str
    title: str
    chunk_count: int
    collection: str


class RetrievedChunk(BaseModel):
    id: str
    text: str
    metadata: dict[str, str | int] = Field(default_factory=dict)
    distance: float | None = None
    relevance_score: float | None = None
