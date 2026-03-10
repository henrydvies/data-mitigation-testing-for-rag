"""SentenceTransformer-based embedders."""

from typing import Sequence

from sentence_transformers import SentenceTransformer


class SentenceTransformerEmbedder:
    """
    Object that provides text embeddings using a SentenceTransformer model.
    """

    def __init__(self, model_name: str) -> None:
        self._model_name = (model_name or "").strip()
        if not self._model_name:
            raise ValueError("model_name must be a non-empty string.")
        self._model: SentenceTransformer | None = None
        # Load model on init. 
        model = self._get_model()
        self.dim: int = model.get_sentence_embedding_dimension()

    def _get_model(self) -> SentenceTransformer:
        """
        Getter for model instance.
        """
        if self._model is None:
            print(f"[embedders/sentence_transformers] loading model={self._model_name}")
            self._model = SentenceTransformer(self._model_name)
        return self._model

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """
        Generate embeddings for a list of texts.
        """
        model = self._get_model()
        embeddings = model.encode(
            list(texts),
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return embeddings.tolist()

