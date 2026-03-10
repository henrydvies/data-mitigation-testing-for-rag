"""Bench configuration helpers."""

from pathlib import Path


def get_repo_root() -> Path:
    """
    Return the repo root directory.
    """
    return Path(__file__).resolve().parent.parent

