"""CLI Entrypoint, used to run all tests."""

import sys

from bench import config, runner
from bench.rag_client import RAGClient
from bench.scenarios import get_run_specs_for_cli


def main() -> int:
    """
    Usage: python run.py <seed|query|run> [scenario_id [scenario_id variant_key ...] | --all]
    With --all: run all scenario x variant combinations.
    Without: run the given scenario(s); each name can be "scenario_id" or "scenario_id variant_key".
    """
    argv = sys.argv[1:]
    if not argv:
        print(
            "Usage: python run.py <seed|query|run> [scenario_id [scenario_id variant_key ...] | --all]",
            file=sys.stderr,
        )
        return 1
    subcommand = argv[0].lower()
    if subcommand not in ("seed", "query", "run"):
        print("Subcommand must be seed, query, or run.", file=sys.stderr)
        return 1
    rest = argv[1:]
    all_flag = "--all" in rest
    if all_flag:
        rest = [a for a in rest if a != "--all"]
    repo_root = config.get_repo_root()
    client = RAGClient()
    try:
        run_specs = get_run_specs_for_cli(repo_root, rest if not all_flag else None, all_flag)
    except (ValueError, FileNotFoundError) as e:
        print(e, file=sys.stderr)
        return 1
    print(f"[run.py] {subcommand}: {len(run_specs)} run(s) (scenario x variant)")
    try:
        if subcommand == "seed":
            runner.seed(run_specs, repo_root, client)
        elif subcommand == "query":
            runner.query(run_specs, repo_root, client)
        else:
            runner.run(run_specs, repo_root, client)
    except SystemExit as e:
        print(e.args[0] if e.args else "Exit", file=sys.stderr)
        return e.code if e.code is not None else 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
