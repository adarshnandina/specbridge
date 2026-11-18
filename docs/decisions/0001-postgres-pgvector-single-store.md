# 0001 - PostgreSQL + pgvector as the single store

## Context
SpecBridge needs relational data (documents, extractions, runs, approvals, audit), full-text search,
vector search, and transactional guarantees (an approval and the state change it triggers must not
diverge). The corpus is small (tens to thousands of documents), the deployment target is one VM.

## Options considered
1. **Postgres + pgvector** for everything (vectors, FTS via `tsvector`, JSONB, relational data).
2. Postgres for relational data + a dedicated vector DB (Qdrant/Weaviate) + Elasticsearch for keyword.
3. SQLite + FAISS in process.

## Decision
Option 1. One `pgvector/pgvector:pg16` container holds every table; chunks carry an HNSW cosine
index on `embedding` and a GIN index on a generated `content_tsv` (`simple` config so part numbers
are not stemmed). Index names (`chunks.index_name`) let experiments keep several chunkings side by
side in one database (used for experiments 1 and 4).

## Consequences
- One backup, one connection string, one failure domain; joins between chunks and documents
  (e.g. "latest revision only") are plain SQL; `agent_runs`/`approvals`/`audit_log` rows commit atomically with state changes.
- Retrieval latency is ~25 ms p50 on 264 chunks (run `20261118-132236_7ca7287_initial-retrieval`);
  this says nothing about scale. HNSW post-filtering by `index_name` needs `hnsw.ef_search` raised
  (set per query); at millions of chunks a dedicated vector store should be re-evaluated.
- The keyword side is Postgres FTS (`ts_rank_cd`), not BM25 (see LIMITATIONS).
