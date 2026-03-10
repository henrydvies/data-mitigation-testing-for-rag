"""Compute metrics and write metrics.json and summary.md for a run."""

import json
from pathlib import Path


def write_run_artifacts(run_dir: Path, results: list[dict], state: dict, config: dict) -> None:
    """
    Write metrics.json and summary.md for a run, based on query results, state, and config.
    """
    doc_id_to_path: dict[str, str] = {
        d["document_id"]: d["corpus_path"] for d in state.get("documents", [])
    }
    metrics_queries: list[dict] = []
    summary_lines: list[str] = []

    for item in results:
        qid = item.get("id", "")
        response_results = item.get("response", {}).get("results", [])
        if not response_results:
            metrics_queries.append({"query_id": qid, "rank1_document_id": None, "rank1_score": None, "results": []})
            summary_lines.append(f"- **{qid}**: no results")
            continue
        first = response_results[0]
        rank1_doc_id = first.get("document_id")
        rank1_score = first.get("score")
        rank1_path = doc_id_to_path.get(str(rank1_doc_id), str(rank1_doc_id))
        result_summary = [
            {"document_id": r.get("document_id"), "score": r.get("score")}
            for r in response_results
        ]
        metrics_queries.append({
            "query_id": qid,
            "rank1_document_id": rank1_doc_id,
            "rank1_score": rank1_score,
            "rank1_corpus_path": rank1_path,
            "results": result_summary,
        })
        summary_lines.append(f"- **{qid}**: rank 1 = {rank1_path} (score={rank1_score})")

    metrics = {
        "queries": metrics_queries,
    }
    (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    summary = "# Run summary\n\n" + "\n".join(summary_lines) + "\n"
    (run_dir / "summary.md").write_text(summary, encoding="utf-8")

