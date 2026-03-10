## SQL models for documents, chunks, and embeddings. 

from datetime import datetime
from typing import Any
import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Document(Base):
    """
    Represents the document table in the database.
    """
    
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    source_type = Column(String, nullable=False)
    source_uri = Column(Text)
    title = Column(Text)
    raw_content = Column(Text)
    metadata_json = Column("metadata", JSONB, default=dict, server_default="{}")
    is_active = Column(Boolean, default=True, server_default="true")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")


class Chunk(Base):    
    """
    Represents the chunk table in the database.
    """
    __tablename__ = "chunks"
    __table_args__ = (UniqueConstraint("document_id", "chunk_index", name="ux_chunks_document_index"),)

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_index = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    metadata_json = Column("metadata", JSONB, default=dict, server_default="{}")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    document = relationship("Document", back_populates="chunks")
    embeddings = relationship(
        "ChunkEmbedding",
        back_populates="chunk",
        cascade="all, delete-orphan",
    )


class ChunkEmbedding(Base):
    """
    Represents the chunk_embeddings table in the database.
    """
    __tablename__ = "chunk_embeddings"
    __table_args__ = (UniqueConstraint("chunk_id", "embedder_name", name="ux_chunk_embeddings_chunk_embedder"),)

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    chunk_id = Column(
        UUID(as_uuid=True),
        ForeignKey("chunks.id", ondelete="CASCADE"),
        nullable=False,
    )
    embedder_name = Column(String, nullable=False)
    embedding_dim = Column(Integer, nullable=False, server_default="384")
    embedding = Column(Vector(384), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    chunk = relationship("Chunk", back_populates="embeddings")

