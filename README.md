# Data mitigation testing for RAG

Benchmark for evaluating **retrieval-level data poisoning** and **multi-embedding as a defence**. Uses an in-process RAG pipeline (ingestion, chunking, embedding, retrieval) and runs test cases that compare single-embedding vs multi-embedding consensus retrieval on clean and poisoned corpora (e.g. policy docs, NQ, PoisonedRAG-style, stealth poison / PIA).

## What it uses

- **Python 3** with **Postgres** and **pgvector** for vector storage
- **Sentence-transformers** for embeddings (primary + optional secondary for multi-embed)
- **rag_pipeline**: in-process pipeline (chunking, dual embeddings, single or multi_consensus retrieval)
- **rag_poisoning_bench**: test-case runner (seed corpus → query → write results and metrics per run)

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

6. **(Optional) Seed Tests**
  Seed the tests. Upload them/ chunk/ embed.
  ```bash
  python rag_poisoning_bench/run.py seed --all

7. **(Optional) Query Pipeline**
  Run test queries on the existing corpus.
  ```bash
  python rag_poisoning_bench/run.py query --all