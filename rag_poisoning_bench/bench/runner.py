"""Runner for RAG poisoning benchmark: seed and query test cases, write results and metrics."""

import json
from datetime import datetime, timezone
from pathlib import Path

from bench.rag_client import RAGClient
from bench.state import read_state, write_state
from bench.test_case import load_config, load_queries, resolve_corpus_path


def resolve_test_names(repo_root: Path, names: list[str] | None, all_flag: bool) -> list[str]:
    """
    Resolve test case names to run, validating they exist under test-cases/.
    """
    test_cases_dir = repo_root / "test-cases"
    if not test_cases_dir.is_dir():
        raise FileNotFoundError(f"test-cases directory not found: {test_cases_dir}")
    if all_flag:
        result = [
            p.name
            for p in test_cases_dir.iterdir()
            if p.is_dir() and not p.name.startswith(".")
        ]
        if not result:
            raise ValueError("No test case directories found under test-cases/")
        return sorted(result)
    if not names:
        raise ValueError("Provide test case name(s) or use --all")
    for name in names:
        path = test_cases_dir / name
        if not path.is_dir():
            raise FileNotFoundError(f"Test case directory not found: {path}")
    return names


def seed(test_names: list[str], repo_root: Path, client: RAGClient) -> None:
    """
    For each test: upload corpus documents if not already uploaded. Then write state/corpus_used.json.
    """
    for name in test_names:
        print(f"[runner] Seeding test: {name}")
        test_path = repo_root / "test-cases" / name
        config = load_config(test_path)
        state_path = test_path / "state" / "corpus_used.json"
        existing = read_state(state_path)
        if existing and existing.get("hasUploaded") is True:
            print(f"[runner] {name} already uploaded, skipping seed")
            continue
        documents: list[dict] = []
        for corpus_path_str in config["corpus_paths"]:
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


def query(test_names: list[str], repo_root: Path, client: RAGClient) -> None:
    """
    For each test: run queries, write runs/<timestamp>/results.json and call metrics for metrics.json/summary.md.
    """
    from bench.metrics import write_run_artifacts

    for name in test_names:
        print(f"[runner] Query test: {name}")
        test_path = repo_root / "test-cases" / name
        state_path = test_path / "state" / "corpus_used.json"
        existing = read_state(state_path)
        if not existing or not existing.get("hasUploaded"):
            raise SystemExit(f"Run seed first for test '{name}'. Missing or not uploaded: {state_path}")
        document_ids = [d["document_id"] for d in existing["documents"]]
        config = load_config(test_path)
        queries_list = load_queries(test_path)
        top_k = config.get("top_k", 5)
        query_options = config.get("query_options", {}) or {}
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        run_dir = test_path / "runs" / timestamp
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
        write_run_artifacts(run_dir, results, existing, config)
        print(f"[runner] Wrote results, metrics, summary to {run_dir}")


def run(test_names: list[str], repo_root: Path, client: RAGClient) -> None:
    """
    Seed (if needed) then query for each test.
    """
    print("[runner] run: seed then query")
    seed(test_names, repo_root, client)
    query(test_names, repo_root, client)

