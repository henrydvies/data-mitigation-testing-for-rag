"""Configuration for the mono-repo RAG pipeline."""

import os

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()


class Settings(BaseModel):
    """
    Default configuration settings for the RAG pipeline.
    """
    # Database , set in .env
    database_url: str = os.getenv("DATABASE_URL", "").strip()

    # Chunking defaults
    chunk_size: int = 400
    chunk_overlap: int = 40

    # Embedding configuration
    primary_embedder_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    primary_embedder_name: str = "all-MiniLM-L6-v2"
    
    secondary_embedder_model: str = "sentence-transformers/paraphrase-MiniLM-L3-v2"
    secondary_embedder_name: str = "paraphrase-MiniLM-L3-v2"
    
    # Embedding shape and batching.
    embedding_dim: int = 384
    embed_batch_size: int = 64

    # Retrieval configuration
    default_retrieval_mode: str = "single"
    multi_embed_enabled: bool = True

    # Pipeline configuration
    ingestion_pipeline_name: str = "basic"
    chunker_name: str = "fixed"

    def __init__(self, **data):
        super().__init__(**data)

        if not self.database_url:
            raise ValueError(
                "DATABASE_URL is not set. "
                "Set it to your Postgres connection string (with pgvector enabled)."
            )


settings = Settings()

