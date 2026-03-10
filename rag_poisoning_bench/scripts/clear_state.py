"""
Delete all test-case state files (state/corpus_used.json) so the next run will re-seed.
Run from repo root: python rag_poisoning_bench/scripts/clear_state.py
"""

import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    test_cases_dir = repo_root / "test-cases"
    if not test_cases_dir.is_dir():
        print(f"No test-cases dir at {test_cases_dir}", file=sys.stderr)
        return 1

    state_files = []
    for tc in sorted(test_cases_dir.iterdir()):
        if tc.is_dir() and not tc.name.startswith("."):
            state_file = tc / "state" / "corpus_used.json"
            if state_file.is_file():
                state_files.append(state_file)

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
