"""Runner for RAG poisoning benchmark: seed and query from scenarios, write results and metrics."""

import json
from datetime import datetime, timezone
from pathlib import Path

from bench.rag_client import RAGClient
from bench.scenarios import get_run_specs_for_cli, load_query_set
from bench.state import read_state, write_state
from bench.test_case import resolve_corpus_path


def seed(run_specs: list[dict], repo_root: Path, client: RAGClient) -> None:
    """
    For each unique state_key: upload corpus documents if not already uploaded.
    Writes test-cases/state/<state_key>.json.
    """
    # Group by state_key, as group shares the same corpus_paths
    seen_state_keys: set[str] = set()
    for spec in run_specs:
        state_key = spec["state_key"]
        if state_key in seen_state_keys:
            continue
        seen_state_keys.add(state_key)

        state_path = repo_root / "test-cases" / "state" / f"{state_key}.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)
        existing = read_state(state_path)
        if existing and existing.get("hasUploaded") is True:
            print(f"[runner] state {state_key} already uploaded, skipping seed")
            continue

        corpus_paths = spec["corpus_paths"]
        documents: list[dict] = []
        for corpus_path_str in corpus_paths:
            print(f"[runner] Uploading corpus: {corpus_path_str}")
            file_path = resolve_corpus_path(repo_root, corpus_path_str)
            raw_content = file_path.read_text(encoding="utf-8")
            title = file_path.stem or None
            doc_id = client.upload_document(raw_content=raw_content, title=title)
            documents.append({"corpus_path": corpus_path_str, "document_id": doc_id})
            print(f"[runner] Uploaded {corpus_path_str} -> document_id={doc_id}")

        state = {
            "hasUploaded": True,
            "documents": documents,
            "seeded_at": datetime.now(timezone.utc).isoformat(),
        }
        write_state(state_path, state)
        print(f"[runner] Wrote state: {state_path}")


def query(run_specs: list[dict], repo_root: Path, client: RAGClient) -> None:
    """
    For each run spec: run queries, write results/<scenario_id>/<variant_key>/runs/<timestamp>/
    with results.json, metrics.json, summary.md, run_manifest.json.
    """
    from bench.metrics import write_run_artifacts

    for spec in run_specs:
        scenario_id = spec["scenario_id"]
        variant_key = spec["variant_key"]
        state_key = spec["state_key"]
        state_path = repo_root / "test-cases" / "state" / f"{state_key}.json"
        existing = read_state(state_path)
        if not existing or not existing.get("hasUploaded"):
            raise SystemExit(
                f"Run seed first for state '{state_key}' (scenario={scenario_id}, variant={variant_key}). "
                f"Missing or not uploaded: {state_path}"
            )

        document_ids = [d["document_id"] for d in existing["documents"]]
        queries_list = load_query_set(repo_root, spec["query_set_id"])
        top_k = spec.get("top_k", 5)
        query_options = spec.get("query_options") or {}

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        run_dir = repo_root / "test-cases" / "results" / scenario_id / variant_key / "runs" / timestamp
        run_dir.mkdir(parents=True, exist_ok=True)
        print(f"[runner] Run dir: {run_dir}")

        results: list[dict] = []
        for q in queries_list:
            qid = q.get("id", "")
            qtext = q["text"]
            print(f"[runner] Query id={qid} ...")
            response_results = client.query_documents(
                qtext,
                document_ids=document_ids,
                top_k=top_k,
                **query_options,
            )
            results.append({"id": qid, "query": qtext, "response": {"results": response_results}})
            print(f"[runner] Query {qid} returned {len(response_results)} results")

        (run_dir / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")

        config = {"corpus_paths": spec["corpus_paths"]}
        write_run_artifacts(run_dir, results, existing, config)

        run_manifest = {
            "scenario_id": scenario_id,
            "variant_key": variant_key,
            "timestamp": timestamp,
            "corpus_paths": spec["corpus_paths"],
            "query_options": query_options,
            "top_k": top_k,
            "query_set_id": spec["query_set_id"],
        }
        (run_dir / "run_manifest.json").write_text(
            json.dumps(run_manifest, indent=2), encoding="utf-8"
        )

        print(f"[runner] Wrote results, metrics, summary, run_manifest to {run_dir}")


def run(run_specs: list[dict], repo_root: Path, client: RAGClient) -> None:
    """Seed (if needed) then query for each run spec."""
    print("[runner] run: seed then query")
    seed(run_specs, repo_root, client)
    query(run_specs, repo_root, client)
