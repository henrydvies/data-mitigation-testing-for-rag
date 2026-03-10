"""Chunking strategies for splitting documents into text chunks."""

from typing import Protocol


class Chunker(Protocol):
    """Protocol for chunkers."""

    def __call__(self, text: str, *, chunk_size: int, overlap: int) -> list[str]:
        ...


def get_chunker(name: str, **_: object) -> Chunker:
    """
    Return a chunker by name.
    
    Just fixed at the moment.
    """
    name = (name or "fixed").lower()
    if name == "fixed":
        from .fixed_size import FixedSizeChunker

        return FixedSizeChunker()
    raise ValueError(f"Unknown chunker: {name}")

