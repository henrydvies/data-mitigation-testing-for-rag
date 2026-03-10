"""Schemas for the Query and Upload results and options."""

from dataclasses import dataclass
from typing import Sequence
from uuid import UUID


@dataclass
class UploadResult:
    document_id: str
    chunks_inserted: int
    embeddings_inserted: int


@dataclass
class QueryResult:
    document_id: UUID
    chunk_id: UUID
    text: str
    score: float


@dataclass
class QueryRequestOptions:
    retrieval_mode: str | None = None
    primary_embedder_name: str | None = None
    secondary_embedder_name: str | None = None
    document_ids: Sequence[str] | None = None
    top_k: int = 5

