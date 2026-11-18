# Eval run `20261118-134901_ba6fde4_exp3-hybrid-rerank`

- suites: retrieval · split: **test** · provider: fake
- git: `ba6fde4` · created 2026-11-18T13:49:01 · duration 28.57 s · cost $0.0000
- embedding model: BAAI/bge-small-en-v1.5 · models: n/a
- prompt versions: n/a
- config: `{"name": "exp3-hybrid-rerank", "description": "Exp 3: hybrid + cross-encoder rerank (BAAI/bge-reranker-base) of the fused top 20.", "index_name": "main", "retrieval": {"mode": "hybrid", "rerank": true}, "qa": {}, "extraction": {}, "agent": {}}`

## Retrieval

| metric | value [95% CI] |
|---|---|
| recall_at_1 | 0.811 [0.658, 0.905] (n=37) |
| recall_at_3 | 0.919 [0.787, 0.972] (n=37) |
| recall_at_5 | 0.919 [0.787, 0.972] (n=37) |
| recall_at_10 | 0.946 [0.823, 0.985] (n=37) |
| mrr | 0.868 (n=37) |

| type | n | recall@5 | mrr |
|---|---|---|---|
| cross_doc | 6 | 0.667 [0.300, 0.903] (n=6) | 0.604 |
| factual | 14 | 0.929 [0.685, 0.987] (n=14) | 0.893 |
| injection | 2 | 1.000 [0.342, 1.000] (n=2) | 1.000 |
| open | 4 | 1.000 [0.510, 1.000] (n=4) | 0.875 |
| revision | 3 | 1.000 [0.439, 1.000] (n=3) | 1.000 |
| table_lookup | 8 | 1.000 [0.676, 1.000] (n=8) | 0.938 |

## Ops

```json
{
 "retrieval": {
  "retrieval_latency_ms": {
   "n": 37,
   "p50": 805.0,
   "p95": 836.6,
   "mean": 770.8648648648649
  }
 }
}
```
