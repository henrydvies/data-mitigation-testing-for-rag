"""Client for Rag pipeline."""

from rag_pipeline.pipeline import Pipeline


class RAGClient:
    """
    Object that represents a client for the RAG pipeline, allowing document uploads and queries.
    """

    def __init__(self) -> None:
        """
        Hold a Pipeline instance configured from config.
        """
        self._pipeline = Pipeline()

    def upload_document(
        self,
        raw_content: str,
        title: str | None = None,
        metadata: dict | None = None,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> str:
        """
        Upload a document to the pipeline, returning the document ID.
        """
        result = self._pipeline.upload_document(
            source_type="manual",
            raw_content=raw_content,
            source_uri=None,
            title=title,
            metadata=metadata or {},
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        print(f"[rag_client] upload -> document_id={result.document_id}")
        return result.document_id

    def query_documents(
        self,
        query: str,
        document_ids: list[str] | None,
        top_k: int = 5,
        **extra: object,
    ) -> list[dict]:
        """
        Query the pipeline, returning a list of results with document_id, chunk_id, text, and score.
        """
        retrieval_mode = str(extra.get("retrieval_mode", "single"))
        primary_name = extra.get("primary_embedder_name")
        secondary_name = extra.get("secondary_embedder_name")

        results = self._pipeline.query_documents(
            query=query,
            document_ids=document_ids or [],
            top_k=top_k,
            retrieval_mode=retrieval_mode,
            primary_embedder_name=primary_name if isinstance(primary_name, str) else None,
            secondary_embedder_name=secondary_name if isinstance(secondary_name, str) else None,
        )
        out: list[dict] = [
            {
                "document_id": str(r.document_id),
                "chunk_id": str(r.chunk_id),
                "text": r.text,
                "score": r.score,
            }
            for r in results
        ]
        print(f"[rag_client] query -> {len(out)} results")
        return out

