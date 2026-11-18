# Eval run `20261118-134750_ba6fde4_exp3-hybrid-rerank`

- suites: retrieval · split: **dev** · provider: fake
- git: `ba6fde4` · created 2026-11-18T13:47:50 · duration 48.41 s · cost $0.0000
- embedding model: BAAI/bge-small-en-v1.5 · models: n/a
- prompt versions: n/a
- config: `{"name": "exp3-hybrid-rerank", "description": "Exp 3: hybrid + cross-encoder rerank (BAAI/bge-reranker-base) of the fused top 20.", "index_name": "main", "retrieval": {"mode": "hybrid", "rerank": true}, "qa": {}, "extraction": {}, "agent": {}}`

## Retrieval

| metric | value [95% CI] |
|---|---|
| recall_at_1 | 0.875 [0.764, 0.938] (n=56) |
| recall_at_3 | 0.946 [0.854, 0.982] (n=56) |
| recall_at_5 | 0.946 [0.854, 0.982] (n=56) |
| recall_at_10 | 0.946 [0.854, 0.982] (n=56) |
| mrr | 0.908 (n=56) |

| type | n | recall@5 | mrr |
|---|---|---|---|
| cross_doc | 9 | 1.000 [0.701, 1.000] (n=9) | 0.870 |
| factual | 21 | 0.905 [0.711, 0.974] (n=21) | 0.905 |
| injection | 3 | 1.000 [0.439, 1.000] (n=3) | 1.000 |
| open | 6 | 1.000 [0.610, 1.000] (n=6) | 1.000 |
| revision | 5 | 0.800 [0.376, 0.964] (n=5) | 0.700 |
| table_lookup | 12 | 1.000 [0.757, 1.000] (n=12) | 0.958 |

## Ops

```json
{
 "retrieval": {
  "retrieval_latency_ms": {
   "n": 56,
   "p50": 810.0,
   "p95": 841.0,
   "mean": 805.7678571428571
  }
 }
}
```
