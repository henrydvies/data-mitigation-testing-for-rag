"""Embedder providers used for document and query embeddings."""

from typing import Protocol, Sequence
from .sentence_transformers import SentenceTransformerEmbedder


class Embedder(Protocol):
    """Protocol for embedding providers."""

    dim: int

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """
        Returns embeddings for the given list of texts.
        """
        ...


def get_embedder(model_name: str):
    """
    Construct an embedder for the given model name.
    """
    
    return SentenceTransformerEmbedder(model_name=model_name)

