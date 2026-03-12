"""
Delete all test-case state files (test-cases/state/*.json) so the next run will re-seed.
Run from repo root: python rag_poisoning_bench/scripts/clear_state.py
"""

import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    state_dir = repo_root / "test-cases" / "state"
    if not state_dir.is_dir():
        print("No test-cases/state dir found.")
        return 0

    state_files = sorted(state_dir.glob("*.json"))
    if not state_files:
        print("No state files found.")
        return 0

    for path in state_files:
        path.unlink()
        print(f"Deleted {path.relative_to(repo_root)}")
    print(f"Cleared {len(state_files)} state file(s). Next run will re-seed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
