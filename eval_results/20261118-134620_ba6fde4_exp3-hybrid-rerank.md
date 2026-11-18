# Eval run `20261118-134620_ba6fde4_exp3-hybrid-rerank`

- suites: retrieval · split: **dev** · provider: fake
- git: `ba6fde4` · created 2026-11-18T13:46:20 · duration 44.37 s · cost $0.0000
- embedding model: BAAI/bge-small-en-v1.5 · models: n/a
- prompt versions: n/a
- config: `{"name": "exp3-hybrid-rerank", "description": "Exp 3: hybrid + cross-encoder rerank (BAAI/bge-reranker-base) of the fused top 20.", "index_name": "main", "retrieval": {"mode": "hybrid", "rerank": true}, "qa": {}, "extraction": {}, "agent": {}}`

## Retrieval

| metric | value [95% CI] |
|---|---|
| recall_at_1 | 0.339 [0.229, 0.470] (n=56) |
| recall_at_3 | 0.464 [0.340, 0.593] (n=56) |
| recall_at_5 | 0.589 [0.459, 0.708] (n=56) |
| recall_at_10 | 0.732 [0.604, 0.830] (n=56) |
| mrr | 0.440 (n=56) |

| type | n | recall@5 | mrr |
|---|---|---|---|
| cross_doc | 9 | 1.000 [0.701, 1.000] (n=9) | 0.652 |
| factual | 21 | 0.476 [0.283, 0.676] (n=21) | 0.383 |
| injection | 3 | 1.000 [0.439, 1.000] (n=3) | 0.733 |
| open | 6 | 0.667 [0.300, 0.903] (n=6) | 0.619 |
| revision | 5 | 0.600 [0.231, 0.882] (n=5) | 0.450 |
| table_lookup | 12 | 0.333 [0.138, 0.609] (n=12) | 0.211 |

## Ops

```json
{
 "retrieval": {
  "retrieval_latency_ms": {
   "n": 56,
   "p50": 788.0,
   "p95": 821.0,
   "mean": 791.1607142857143
  }
 }
}
```
