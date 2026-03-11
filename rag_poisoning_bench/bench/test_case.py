"""Resolve corpus paths. Test cases are now defined in scenarios.yaml and query_sets/."""

from pathlib import Path


def resolve_corpus_path(repo_root: Path, corpus_path: str) -> Path:
    """
    Resolve corpus path relative to repo root, ensuring it exists and is a file.
    """
    resolved = (repo_root / corpus_path).resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError:
        raise ValueError(f"Corpus path must be under repo root: {corpus_path}") from None
    if not resolved.exists() or not resolved.is_file():
        raise FileNotFoundError(f"Corpus file not found: {resolved}")
    return resolved
