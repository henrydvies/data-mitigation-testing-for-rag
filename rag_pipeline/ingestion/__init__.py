"""Ingestion strategies to use for uploading documents into the RAG corpus."""

from typing import Protocol
from uuid import UUID

from sqlalchemy.orm import Session


class IngestionPipeline(Protocol):
    """Protocol for ingestion pipelines."""

    def ingest(
        self,
        db: Session,
        *,
        source_type: str,
        source_uri: str | None,
        title: str | None,
        raw_content: str,
        metadata: dict | None,
    ) -> UUID:
        ...


def get_ingestion_pipeline(name: str, **_: object) -> IngestionPipeline:
    """
    Return an ingestion pipeline by name.
    """
    name = (name or "basic").lower()
    if name == "basic":
        from .basic import BasicIngestion

        return BasicIngestion()
    raise ValueError(f"Unknown ingestion pipeline: {name}")

