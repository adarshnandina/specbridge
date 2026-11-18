# 2.2 Retrieval: vector, keyword, hybrid RRF, optional rerank
## Summary
pgvector cosine search, Postgres FTS keyword search (websearch_to_tsquery, OR-combined content words, 'simple' config), RRF fusion (k=60, top 30 each), optional cross-encoder rerank of fused top 20; per-call mode/top_k/rerank/include_superseded/index; vector similarity always computed as abstention signal
## Why
Part of milestone task 2.2 in SPECBRIDGE_SPEC.md Section 13.
## Changes (files/modules)
specbridge/retrieval/* tests/unit/test_retrieval_units.py tests/integration/test_retrieval.py
## How it was tested (commands + results)
unit test_retrieval_units 4 passed; integration test_retrieval 9 passed (3 modes, exact part number, RRF scores, revision filter, index isolation, rerank, bad mode)
## Eval impact (baseline run id → new run id, deltas) or "n/a"
n/a
## Risks / follow-ups
none known
## Self-review checklist
- [x] tests added/updated   - [x] types pass   - [x] lint passes
- [x] no secrets            - [x] logs added for new code paths
- [x] docs updated          - [x] error handling covers failure modes
