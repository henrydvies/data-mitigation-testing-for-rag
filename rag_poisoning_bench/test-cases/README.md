# Test cases Explanation

Test cases are defined in one place and expanded by the runner into scenario × variant runs.

## Layout

- **query_sets/** — One JSON file per query set (list of `{ "id", "text" }`). Referenced by `scenarios.yaml` via `query_set`.
- **scenarios.yaml** — Central list of scenarios and variant dimensions. Runner expands scenario × corpus_type × retrieval_mode (and any future defence dimensions).
- **state/** — Seeding state per corpus set: `state/<scenario_id>_<corpus_type>.json`. Created by `run.py seed`.
- **results/** — Run outputs: `results/<scenario_id>/<variant_key>/runs/<timestamp>/` with `results.json`, `metrics.json`, `summary.md`, `run_manifest.json`.

## Adding a new test case (scenario)

1. Add corpus file(s) under `rag_poisoning_bench/corpus/`.
2. Add `test-cases/query_sets/<id>.json` with queries (list of `{ "id", "text" }`).
3. In `scenarios.yaml`, add a new entry under `scenarios:` with `id`, `name`, `corpus_clean`, `corpus_poison`, `query_set`.

## Adding a new defence

1. Implement the defence in the pipeline (e.g. new `query_options`).
2. In `scenarios.yaml`, add a new block under `variants:` (e.g. `strict_consensus: [{ key: off, ... }, { key: on, query_options: {...} }]`). The runner will run every combination including the new dimension.

## Running

From repo root (with `PYTHONPATH` set to include the repo or `rag_poisoning_bench`):

- `python rag_poisoning_bench/run.py run --all` — run all scenario × variant combinations.
- `python rag_poisoning_bench/run.py run policy_trust` — run all variants for scenario `policy_trust`.
- `python rag_poisoning_bench/run.py run policy_trust poison_multi_embed` — run one variant.
