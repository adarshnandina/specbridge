# Eval run `20261118-142216_f14eb9c_exp3-hybrid-rerank`

- suites: retrieval · split: **dev** · provider: fake
- git: `f14eb9c` · created 2026-11-18T14:22:16 · duration 45.68 s · cost $0.0000
- embedding model: BAAI/bge-small-en-v1.5 · models: n/a
- prompt versions: n/a
- config: `{"name": "exp3-hybrid-rerank", "description": "Exp 3: hybrid + cross-encoder rerank (BAAI/bge-reranker-base) of the fused top 20.", "index_name": "main", "retrieval": {"mode": "hybrid", "rerank": true}, "qa": {}, "extraction": {}, "agent": {}}`

## Retrieval

| metric | value [95% CI] |
|---|---|
| recall_at_1 | 0.893 [0.785, 0.950] (n=56) |
| recall_at_3 | 0.964 [0.879, 0.990] (n=56) |
| recall_at_5 | 0.964 [0.879, 0.990] (n=56) |
| recall_at_10 | 0.964 [0.879, 0.990] (n=56) |
| mrr | 0.923 (n=56) |

| type | n | recall@5 | mrr |
|---|---|---|---|
| cross_doc | 9 | 1.000 [0.701, 1.000] (n=9) | 0.870 |
| factual | 21 | 0.905 [0.711, 0.974] (n=21) | 0.873 |
| injection | 3 | 1.000 [0.439, 1.000] (n=3) | 1.000 |
| open | 6 | 1.000 [0.610, 1.000] (n=6) | 1.000 |
| revision | 5 | 1.000 [0.566, 1.000] (n=5) | 0.900 |
| table_lookup | 12 | 1.000 [0.757, 1.000] (n=12) | 1.000 |

## Ops

```json
{
 "retrieval": {
  "retrieval_latency_ms": {
   "n": 56,
   "p50": 807.5,
   "p95": 876.75,
   "mean": 814.4642857142857
  }
 }
}
```
