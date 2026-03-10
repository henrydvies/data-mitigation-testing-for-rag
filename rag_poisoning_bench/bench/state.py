"""Read and write state/corpus_used.json."""

import json
from pathlib import Path


def read_state(path: Path) -> dict | None:
    """
    Read state from JSON file, returning None if file missing or invalid.
    """
    if not path.exists():
        return None
    try:
        data = path.read_text(encoding="utf-8")
        return json.loads(data)
    except (json.JSONDecodeError, OSError):
        return None  # invalid or unreadable


def write_state(path: Path, state: dict) -> None:
    """
    Write state dict to JSON file, creating parent directories if needed.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")

