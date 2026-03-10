## Basic ingestion strategy

from uuid import UUID

from sqlalchemy.orm import Session

from rag_pipeline import models


class BasicIngestion:
    """Store raw document content and metadata as-is."""

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
        """
        Ingest a document by storing its raw content and metadata in the database.
        """
        doc = models.Document(
            source_type=source_type,
            source_uri=source_uri,
            title=title,
            raw_content=raw_content,
            metadata_json=metadata or {},
        )
        db.add(doc)
        db.flush()
        db.refresh(doc)
        return doc.id

