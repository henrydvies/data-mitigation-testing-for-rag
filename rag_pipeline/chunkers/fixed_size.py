## Basic size n chunks

class FixedSizeChunker:
    """
    Fixed-size character chunker with overlap.
    
    Split document into chunks of specificed size, with overlap between adjacent chunks.
    """

    def __call__(self, text: str, *, chunk_size: int, overlap: int) -> list[str]:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive.")
        if overlap < 0:
            raise ValueError("overlap must be non-negative.")
        if overlap >= chunk_size:
            raise ValueError("overlap must be less than chunk_size.")

        chunks: list[str] = []
        start = 0
        n = len(text)
        if n == 0:
            return chunks

        while start < n:
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            if end >= n:
                break
            start = end - overlap

        return chunks

