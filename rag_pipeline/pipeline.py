"""Central RAG Pipeline."""

from dataclasses import dataclass
from typing import Sequence
from uuid import UUID

from sqlalchemy.orm import Session

from .config import Settings
from .db import SessionFactory
from .ingestion import get_ingestion_pipeline
from .chunkers import get_chunker
from .embedders import get_embedder
from . import retrieval
from .schemas import UploadResult, QueryResult


def _resolve_chunk_params(
    settings: Settings,
    chunk_size: int | None,
    chunk_overlap: int | None,
) -> tuple[int, int]:
    """
    Determine effective chunk size and overlap based on provided parameters or settings defaults.
    """
    size = chunk_size or settings.chunk_size
    overlap = chunk_overlap if chunk_overlap is not None else settings.chunk_overlap
    if overlap >= size:
        raise ValueError("chunk_overlap must be less than chunk_size.")
    return size, overlap


@dataclass
class Pipeline:
    """
    In-process RAG pipeline: ingestion, chunking, embedding, and retrieval.
    
    Configuration is provided by config.py and can be passed in.
    """

    settings: Settings | None = None

    def __post_init__(self) -> None:
        self.settings = self.settings or Settings()
        self._session_factory = SessionFactory(self.settings.database_url)
        self._ingestion = get_ingestion_pipeline(self.settings.ingestion_pipeline_name)
        self._chunker = get_chunker(self.settings.chunker_name)
        self._primary_embedder = get_embedder(self.settings.primary_embedder_model)
        self._secondary_embedder = (
            get_embedder(self.settings.secondary_embedder_model)
            if self.settings.multi_embed_enabled and self.settings.secondary_embedder_model
            else None
        )

    
    def _chunk_and_embed(
        self,
        db: Session,
        document_id: UUID,
        chunk_size: int,
        chunk_overlap: int,
    ) -> tuple[int, int]:
        """
        Helper to chunk and embed a document by id. Used for both initial upload and re-processing.
        """
        document = retrieval.get_document(db, document_id)
        if not document:
            raise ValueError("Document not found.")
        if not document.raw_content:
            raise ValueError("Document has no content to process.")

        # Chunk document text.
        print(
            f"[pipeline] chunking document_id={document_id} "
            f"chunk_size={chunk_size} overlap={chunk_overlap}"
        )
        chunks = self._chunker(
            document.raw_content,
            chunk_size=chunk_size,
            overlap=chunk_overlap,
        )
        if not chunks:
            raise ValueError("Chunker returned no chunks for the document content.")

        # Replace existing chunks and embeddings for this document.
        print(f"[pipeline] deleting existing chunks and embeddings for document_id={document_id}")
        retrieval.delete_chunks_and_embeddings(db, document_id)

        # Insert chunks.
        chunk_models = retrieval.insert_chunks(db, document_id, chunks)

        # Embed with primary embedder in batches.
        print(
            f"[pipeline] embedding {len(chunks)} chunks for document_id={document_id} "
            f"model={self.settings.primary_embedder_model}"
        )
        batch_size = self.settings.embed_batch_size
        dim_primary: int | None = None
        embeddings_inserted = 0

        # Loop over chunks in batches to embed and insert into the database.
        for start in range(0, len(chunks), batch_size):
            end = start + batch_size
            chunk_batch = chunks[start:end]
            model_batch = chunk_models[start:end]
            embeddings_batch = self._primary_embedder.embed(chunk_batch)

            if dim_primary is None:
                dim_primary = self._primary_embedder.dim
                if dim_primary != self.settings.embedding_dim:
                    raise ValueError(
                        f"Embedding dimension {dim_primary} does not match expected {self.settings.embedding_dim}."
                    )
            retrieval.insert_embeddings(
                db,
                model_batch,
                embeddings_batch,
                embedder_name=self.settings.primary_embedder_name,
                embedding_dim=dim_primary,
            )
            embeddings_inserted += len(model_batch)

        # Optionally embed with secondary embedder when multi-embedding is enabled (Used for multi embedding defence).
        if self.settings.multi_embed_enabled and self._secondary_embedder and self.settings.secondary_embedder_name:
            print(
                f"[pipeline] embedding {len(chunks)} chunks for document_id={document_id} "
                f"secondary_model={self.settings.secondary_embedder_model}"
            )
            dim_secondary: int | None = None

            for start in range(0, len(chunks), batch_size):
                end = start + batch_size
                chunk_batch = chunks[start:end]
                model_batch = chunk_models[start:end]
                embeddings_batch = self._secondary_embedder.embed(chunk_batch)

                if dim_secondary is None:
                    dim_secondary = self._secondary_embedder.dim
                    if dim_secondary != self.settings.embedding_dim:
                        raise ValueError(
                            f"Embedding dimension {dim_secondary} does not match expected {self.settings.embedding_dim}."
                        )
                retrieval.insert_embeddings(
                    db,
                    model_batch,
                    embeddings_batch,
                    embedder_name=self.settings.secondary_embedder_name,
                    embedding_dim=dim_secondary,
                )

            embeddings_inserted = len(chunk_models) * 2

        return len(chunk_models), embeddings_inserted

    def upload_document(
        self,
        *,
        source_type: str,
        raw_content: str,
        source_uri: str | None = None,
        title: str | None = None,
        metadata: dict | None = None,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> UploadResult:
        """
        Ingest one document, then chunk and embed it.
        """
        settings = self.settings or Settings()
        size, overlap = _resolve_chunk_params(settings, chunk_size, chunk_overlap)

        # Ingest document and get assigned document_id, then chunk and embed within the same transaction.
        with self._session_factory() as db:
            with db.begin():
                document_id = self._ingestion.ingest(
                    db,
                    source_type=source_type,
                    source_uri=source_uri,
                    title=title,
                    raw_content=raw_content,
                    metadata=metadata or {},
                )
                chunks_count, embeddings_count = self._chunk_and_embed(
                    db=db,
                    document_id=document_id,
                    chunk_size=size,
                    chunk_overlap=overlap,
                )

        print(f"[pipeline] upload completed document_id={document_id} chunks={chunks_count}")
        return UploadResult(
            document_id=str(document_id),
            chunks_inserted=chunks_count,
            embeddings_inserted=embeddings_count,
        )

    def process_document(
        self,
        document_id: str | UUID,
        *,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> UploadResult:
        """
        Re-chunk and re-embed an existing document.
        """
        settings = self.settings or Settings()
        size, overlap = _resolve_chunk_params(settings, chunk_size, chunk_overlap)
        doc_uuid = UUID(str(document_id))

        with self._session_factory() as db:
            with db.begin():
                chunks_count, embeddings_count = self._chunk_and_embed(
                    db=db,
                    document_id=doc_uuid,
                    chunk_size=size,
                    chunk_overlap=overlap,
                )

        return UploadResult(
            document_id=str(doc_uuid),
            chunks_inserted=chunks_count,
            embeddings_inserted=embeddings_count,
        )

    def query_documents(
        self,
        query: str,
        *,
        document_ids: Sequence[str] | None = None,
        top_k: int = 5,
        retrieval_mode: str | None = None,
        primary_embedder_name: str | None = None,
        secondary_embedder_name: str | None = None,
    ) -> list[QueryResult]:
        """
        Embed the query and retrieve top-k chunks by cosine similarity.
        """
        settings = self.settings or Settings()
        mode = (retrieval_mode or settings.default_retrieval_mode).lower()

        primary_name = primary_embedder_name or settings.primary_embedder_name
        secondary_name = secondary_embedder_name or settings.secondary_embedder_name

        if mode not in ("single", "multi_consensus"):
            raise ValueError(f"Unsupported retrieval_mode '{retrieval_mode}'.")

        if mode != "single" and not settings.multi_embed_enabled:
            raise ValueError("Multi-embedding retrieval is not enabled.")

        if mode == "multi_consensus" and not secondary_name:
            raise ValueError("Secondary embedder is not configured for multi_consensus retrieval.")

        # Convert external string ids to UUIDs for the DB layer.
        doc_uuids: list[UUID] | None = None
        if document_ids is not None:
            doc_uuids = [UUID(str(d)) for d in document_ids]

        with self._session_factory() as db:
            if mode == "single":
                return self._query_single(
                    db,
                    query=query,
                    top_k=top_k,
                    embedder_name=primary_name,
                    document_ids=doc_uuids,
                )
            return self._query_multi_consensus(
                db,
                query=query,
                top_k=top_k,
                primary_name=primary_name,
                secondary_name=secondary_name,
                document_ids=doc_uuids,
            )

    def _query_single(
        self,
        db: Session,
        *,
        query: str,
        top_k: int,
        embedder_name: str,
        document_ids: Sequence[UUID] | None,
    ) -> list[QueryResult]:
        """
        For when using single embedding retrieval.
        Return the top-k most similar chunks to the query based on cosine similarity of embeddings.
        """
        embeddings = self._primary_embedder.embed([query])
        dim = self._primary_embedder.dim
        if dim != self.settings.embedding_dim:
            raise ValueError(
                f"Embedding dimension {dim} does not match expected {self.settings.embedding_dim}."
            )

        query_vector = embeddings[0]
        results = retrieval.search_chunks(
            db_session=db,
            query_embedding=query_vector,
            top_k=top_k,
            embedder_name=embedder_name,
            document_ids=document_ids,
        )
        return [
            QueryResult(
                document_id=row["document_id"],
                chunk_id=row["chunk_id"],
                text=row["text"],
                score=float(row["score"]),
            )
            for row in results
        ]

    def _query_multi_consensus(
        self,
        db: Session,
        *,
        query: str,
        top_k: int,
        primary_name: str,
        secondary_name: str,
        document_ids: Sequence[UUID] | None,
    ) -> list[QueryResult]:
        """
        For when using multi-embedding.
        Retrieve top-k results from both primary and secondary embedders, then combine results by agreement (intersection of chunk_ids) and average rank.
        (Just this method for now when multi)
        """
        if not self._secondary_embedder:
            raise ValueError("Secondary embedder is not configured.")

        emb_primary = self._primary_embedder.embed([query])
        dim_p = self._primary_embedder.dim
        emb_secondary = self._secondary_embedder.embed([query])
        dim_s = self._secondary_embedder.dim

        if dim_p != self.settings.embedding_dim or dim_s != self.settings.embedding_dim:
            raise ValueError("Embedding dimension mismatch for multi-embedding retrieval.")

        query_vec_p = emb_primary[0]
        query_vec_s = emb_secondary[0]

        # Retrieve a slightly larger candidate set to increase chance of overlap.
        raw_k = top_k * 3

        results_p = retrieval.search_chunks(
            db_session=db,
            query_embedding=query_vec_p,
            top_k=raw_k,
            embedder_name=primary_name,
            document_ids=document_ids,
        )
        results_s = retrieval.search_chunks(
            db_session=db,
            query_embedding=query_vec_s,
            top_k=raw_k,
            embedder_name=secondary_name,
            document_ids=document_ids,
        )

        rank_p = {row["chunk_id"]: idx for idx, row in enumerate(results_p)}
        rank_s = {row["chunk_id"]: idx for idx, row in enumerate(results_s)}
        by_id_p = {row["chunk_id"]: row for row in results_p}

        common_ids = set(rank_p.keys()) & set(rank_s.keys())

        combined: list[dict] = []
        for cid in common_ids:
            rp = rank_p[cid]
            rs = rank_s[cid]
            # Lower rank index is better, use average rank as combined score.
            score = (rp + rs) / 2.0
            base = by_id_p[cid]
            combined.append(
                {
                    "chunk_id": base["chunk_id"],
                    "document_id": base["document_id"],
                    "text": base["text"],
                    "score": score,
                }
            )

        # Fallback, if no combination fallback to sorted list.
        if not combined:
            selected = results_p[:top_k]
        else:
            combined.sort(key=lambda r: r["score"])
            selected = combined[:top_k]

        return [
            QueryResult(
                document_id=row["document_id"],
                chunk_id=row["chunk_id"],
                text=row["text"],
                score=float(row["score"]),
            )
            for row in selected
        ]

