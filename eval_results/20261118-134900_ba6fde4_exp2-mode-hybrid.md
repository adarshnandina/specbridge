# Eval run `20261118-134900_ba6fde4_exp2-mode-hybrid`

- suites: retrieval · split: **test** · provider: fake
- git: `ba6fde4` · created 2026-11-18T13:49:00 · duration 1.02 s · cost $0.0000
- embedding model: BAAI/bge-small-en-v1.5 · models: n/a
- prompt versions: n/a
- config: `{"name": "exp2-mode-hybrid", "description": "Exp 2: hybrid (RRF over vector + keyword).", "index_name": "main", "retrieval": {"mode": "hybrid"}, "qa": {}, "extraction": {}, "agent": {}}`

## Retrieval

| metric | value [95% CI] |
|---|---|
| recall_at_1 | 0.486 [0.335, 0.641] (n=37) |
| recall_at_3 | 0.730 [0.570, 0.846] (n=37) |
| recall_at_5 | 0.865 [0.720, 0.941] (n=37) |
| recall_at_10 | 0.919 [0.787, 0.972] (n=37) |
| mrr | 0.635 (n=37) |

| type | n | recall@5 | mrr |
|---|---|---|---|
| cross_doc | 6 | 0.667 [0.300, 0.903] (n=6) | 0.207 |
| factual | 14 | 0.857 [0.601, 0.960] (n=14) | 0.679 |
| injection | 2 | 1.000 [0.342, 1.000] (n=2) | 1.000 |
| open | 4 | 1.000 [0.510, 1.000] (n=4) | 0.750 |
| revision | 3 | 1.000 [0.439, 1.000] (n=3) | 0.667 |
| table_lookup | 8 | 0.875 [0.529, 0.978] (n=8) | 0.719 |

## Ops

```json
{
 "retrieval": {
  "retrieval_latency_ms": {
   "n": 37,
   "p50": 26.0,
   "p95": 29.80000000000001,
   "mean": 26.405405405405407
  }
 }
}
```
