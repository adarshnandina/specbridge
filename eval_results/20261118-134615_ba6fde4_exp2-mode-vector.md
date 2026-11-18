# Eval run `20261118-134615_ba6fde4_exp2-mode-vector`

- suites: retrieval · split: **dev** · provider: fake
- git: `ba6fde4` · created 2026-11-18T13:46:15 · duration 1.24 s · cost $0.0000
- embedding model: BAAI/bge-small-en-v1.5 · models: n/a
- prompt versions: n/a
- config: `{"name": "exp2-mode-vector", "description": "Exp 2: vector (pgvector cosine) only.", "index_name": "main", "retrieval": {"mode": "vector"}, "qa": {}, "extraction": {}, "agent": {}}`

## Retrieval

| metric | value [95% CI] |
|---|---|
| recall_at_1 | 0.607 [0.476, 0.724] (n=56) |
| recall_at_3 | 0.821 [0.702, 0.900] (n=56) |
| recall_at_5 | 0.875 [0.764, 0.938] (n=56) |
| recall_at_10 | 0.964 [0.879, 0.990] (n=56) |
| mrr | 0.722 (n=56) |

| type | n | recall@5 | mrr |
|---|---|---|---|
| cross_doc | 9 | 0.778 [0.453, 0.937] (n=9) | 0.465 |
| factual | 21 | 0.857 [0.654, 0.950] (n=21) | 0.750 |
| injection | 3 | 1.000 [0.439, 1.000] (n=3) | 1.000 |
| open | 6 | 1.000 [0.610, 1.000] (n=6) | 0.867 |
| revision | 5 | 0.600 [0.231, 0.882] (n=5) | 0.392 |
| table_lookup | 12 | 1.000 [0.757, 1.000] (n=12) | 0.861 |

## Ops

```json
{
 "retrieval": {
  "retrieval_latency_ms": {
   "n": 56,
   "p50": 22.0,
   "p95": 23.0,
   "mean": 21.125
  }
 }
}
```
