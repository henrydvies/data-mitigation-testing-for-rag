"""Load scenarios.yaml and expand to run specs (scenario × variant dimensions)."""

import json
from pathlib import Path
from typing import Any

import yaml


def load_scenarios_yaml(repo_root: Path) -> dict[str, Any]:
    """Load and parse test-cases/scenarios.yaml."""
    path = repo_root / "test-cases" / "scenarios.yaml"
    if not path.exists():
        raise FileNotFoundError(f"scenarios.yaml not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("scenarios.yaml must be a YAML object")
    return data


def expand_corpus_paths(repo_root: Path, path_list: list[str]) -> list[str]:
    """
    Expand corpus path list: if a path is a directory, replace it with
    sorted relative paths of all .txt files inside; otherwise keep the path.
    Paths remain relative to repo_root.
    """
    result: list[str] = []
    for p in path_list:
        full = repo_root / p
        if full.is_dir():
            for f in sorted(full.glob("*.txt")):
                result.append(f.relative_to(repo_root).as_posix())
        else:
            result.append(p)
    return result


def load_query_set(repo_root: Path, query_set_id: str) -> list[dict]:
    """Load query set from test-cases/query_sets/<id>.json."""
    path = repo_root / "test-cases" / "query_sets" / f"{query_set_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"query set not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"query set {query_set_id} must be a JSON array")
    for i, item in enumerate(data):
        if not isinstance(item, dict) or "text" not in item:
            raise ValueError(f"query_sets/{query_set_id}.json[{i}] must have 'text'")
    return data


def expand_scenarios(repo_root: Path) -> list[dict]:
    """
    Expand scenarios × variant dimensions into a list of run specs.
    Each run spec has: scenario_id, variant_key, corpus_paths, query_set_id,
    query_options (merged), state_key, top_k.
    """
    data = load_scenarios_yaml(repo_root)
    scenarios = data.get("scenarios")
    variants = data.get("variants")
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError("scenarios.yaml must have a non-empty 'scenarios' list")
    if not isinstance(variants, dict) or not variants:
        raise ValueError("scenarios.yaml must have a 'variants' object")

    # Order of dimensions: corpus type, retrieval mode, and more soon
    dimension_names = list(variants.keys())
    run_specs: list[dict] = []

    for scenario in scenarios:
        if not isinstance(scenario, dict):
            continue
        scenario_id = scenario.get("id")
        if not scenario_id:
            continue
        query_set_id = scenario.get("query_set")
        if not query_set_id:
            continue
        corpus_clean = scenario.get("corpus_clean") or []
        corpus_poison = scenario.get("corpus_poison") or []
        if not isinstance(corpus_clean, list) or not isinstance(corpus_poison, list):
            continue

        # Relative path strings (for state and config); expand directories to .txt files
        corpus_clean_strs = expand_corpus_paths(
            repo_root, [p for p in corpus_clean if isinstance(p, str)]
        )
        corpus_poison_strs = expand_corpus_paths(
            repo_root, [p for p in corpus_poison if isinstance(p, str)]
        )

        # Iterate over all combinations of dimension values
        def recurse(dim_index: int, key_parts: list[str], merged_options: dict) -> None:
            if dim_index >= len(dimension_names):
                variant_key = "_".join(key_parts)
                # key_parts[0] is corpus_type (clean or poison)
                corpus_type = key_parts[0] if key_parts else "clean"
                corpus_paths = corpus_poison_strs if corpus_type == "poison" else corpus_clean_strs
                if not corpus_paths:
                    return
                state_key = f"{scenario_id}_{corpus_type}"
                run_specs.append({
                    "scenario_id": scenario_id,
                    "variant_key": variant_key,
                    "corpus_paths": list(corpus_paths),
                    "query_set_id": query_set_id,
                    "query_options": dict(merged_options),
                    "state_key": state_key,
                    "top_k": 5,
                })
                return

            dim_name = dimension_names[dim_index]
            dim_list = variants.get(dim_name)
            if not isinstance(dim_list, list):
                recurse(dim_index + 1, key_parts, merged_options)
                return

            for v in dim_list:
                if not isinstance(v, dict):
                    continue
                k = v.get("key")
                if not k:
                    continue
                opts = v.get("query_options")
                if isinstance(opts, dict):
                    next_options = {**merged_options, **opts}
                else:
                    next_options = merged_options
                recurse(dim_index + 1, key_parts + [k], next_options)

        recurse(0, [], {})

    return run_specs


def get_run_specs_for_cli(repo_root: Path, names: list[str] | None, all_flag: bool) -> list[dict]:
    """
    Resolve CLI args to a list of run specs.
    If all_flag: return all run specs.
    If names: each name is either scenario_id (all variants for that scenario)
    or "scenario_id variant_key" (single variant). Return matching run specs.
    """
    all_specs = expand_scenarios(repo_root)
    if all_flag:
        return all_specs
    if not names:
        raise ValueError("Provide scenario id(s) or use --all")

    result: list[dict] = []
    for name in names:
        parts = name.split(None, 1)
        scenario_id = parts[0]
        variant_key = parts[1] if len(parts) > 1 else None
        for spec in all_specs:
            if spec["scenario_id"] != scenario_id:
                continue
            if variant_key is None or spec["variant_key"] == variant_key:
                result.append(spec)
    if not result and names:
        raise ValueError(f"No run specs matched: {names}")
    return result
