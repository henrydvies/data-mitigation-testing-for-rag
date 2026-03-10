"""CRUD helpers and vector search over chunk embeddings."""

from typing import Iterable, List, Sequence
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from . import models


def get_document(db_session: Session, document_id: UUID) -> models.Document | None:
    return db_session.get(models.Document, document_id)


def delete_chunks_and_embeddings(db_session: Session, document_id: UUID) -> None:
    """
    Delete existing chunks (and cascade embeddings) for a document.
    """
    db_session.execute(
        delete(models.Chunk).where(models.Chunk.document_id == document_id)
    )


def insert_chunks(db_session: Session, document_id: UUID, chunk_texts: Sequence[str]) -> List[models.Chunk]:
    """
    Insert chunks for a document.
    """
    chunks: list[models.Chunk] = []
    for idx, text in enumerate(chunk_texts):
        chunks.append(
            models.Chunk(
                document_id=document_id,
                chunk_index=idx,
                text=text,
                metadata_json={},
            )
        )
    db_session.add_all(chunks)
    db_session.flush()
    return chunks


def insert_embeddings(
    db_session: Session,
    chunks: Sequence[models.Chunk],
    embeddings: Sequence[Sequence[float]],
    embedder_name: str,
    embedding_dim: int,
) -> None:
    """
    Insert embeddings for chunks.
    """
    if len(chunks) != len(embeddings):
        raise ValueError("Number of embeddings does not match number of chunks.")

    records: list[models.ChunkEmbedding] = []
    for chunk, vector in zip(chunks, embeddings):
        records.append(
            models.ChunkEmbedding(
                chunk_id=chunk.id,
                embedder_name=embedder_name,
                embedding_dim=embedding_dim,
                embedding=list(vector),
            )
        )
    db_session.add_all(records)


def search_chunks(
    db_session: Session,
    query_embedding: Sequence[float],
    top_k: int,
    embedder_name: str,
    document_ids: Iterable[UUID] | None = None,
):
    """
    Vector similarity search using pgvector cosine distance.
    """
    distance_expr = models.ChunkEmbedding.embedding.cosine_distance(query_embedding)

    stmt = (
        select(
            models.Chunk.id.label("chunk_id"),
            models.Chunk.document_id.label("document_id"),
            models.Chunk.text.label("text"),
            distance_expr.label("distance"),
        )
        .join(models.ChunkEmbedding, models.ChunkEmbedding.chunk_id == models.Chunk.id)
        .where(models.ChunkEmbedding.embedder_name == embedder_name)
        .order_by(distance_expr)
        .limit(top_k)
    )

    if document_ids:
        stmt = stmt.where(models.Chunk.document_id.in_(list(document_ids)))

    result = db_session.execute(stmt).all()

    return [
        {
            "chunk_id": row.chunk_id,
            "document_id": row.document_id,
            "text": row.text,
            "score": row.distance,
        }
        for row in result
    ]

