# Data mitigation testing for RAG

Benchmark for evaluating **retrieval-level data poisoning** and **multi-embedding as a defence**. Uses an in-process RAG pipeline (ingestion, chunking, embedding, retrieval) and runs test cases that compare single-embedding vs multi-embedding consensus retrieval on clean and poisoned corpora (e.g. policy docs, NQ, PoisonedRAG-style, stealth poison / PIA).

## What it uses

- **Python 3** with **Postgres** and **pgvector** for vector storage
- **Sentence-transformers** for embeddings (primary + optional secondary for multi-embed)
- **rag_pipeline**: in-process pipeline (chunking, dual embeddings, single or multi_consensus retrieval)
- **rag_poisoning_bench**: test-case runner (seed corpus → query → write results and metrics per run)

## Metrics produced by the tests

Each run writes `test-cases/<name>/runs/<timestamp>/metrics.json` and `summary.md`. These align with the retrieval-level evaluation in the project report (Section 3.5).

- **Attack Success Rate (ASR)** — When the corpus includes poisoned documents, ASR is the proportion of queries whose top-ranked (rank-1) result is from a poisoned document. Lower ASR means the defence is reducing how often poison appears first. Compare single-embed vs multi-embed on the same scenario to measure ASR reduction.
- **Clean retrieval rate** — When the corpus is clean-only, the proportion of queries whose rank-1 is from a clean document (should be 100%). Confirms the defence does not harm normal retrieval.
- **Poison-in-top-k rate** — Among runs where poison is present, the proportion of queries that have at least one poisoned document anywhere in the top-k. Complements ASR by measuring poison visibility in the retrieval window.
- **Per-query fields** — Each query has `rank1_is_poison`, `first_clean_rank` (rank of first clean doc in top-k when poison is present), and `poison_at_rank` (ranks where poison appears). Run-level `summary_metrics` aggregate these into ASR, clean retrieval rate, and optional mean first-clean rank and per-rank poison counts.

## Setup

1. **Clone and enter the repo**
   ```bash
   cd data-mitigation-testing-for-rag

2. **Install Dependancies**
   ```bash
   pip install -r requirements.txt

3. **Configure Environment**
   Copy .env.example to .env
   Replace DATABASE_URL with a Postgres connection string for a database with pgvector enabled (Firebase).

4. **Add Test Data**
   Ensure rag_poisoning_bench/test-cases/ has desired test case folders. 

5. **Run Bench from repo root**
   ```bash
   set PYTHONPATH=$CD$
   python rag_poisoning_bench/run.py run --all
   ```

6. **(Optional) Seed Tests**
   Seed the tests. Upload them/ chunk/ embed.
   ```bash
   python rag_poisoning_bench/run.py seed --all
   ```
7. **(Optional) Query Pipeline**
   Run test queries on the existing corpus.
   ```bash
   python rag_poisoning_bench/run.py query --all
   ```