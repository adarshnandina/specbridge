# Eval run `20261118-142308_f14eb9c_exp1-chunking-layout`

- suites: retrieval · split: **test** · provider: fake
- git: `f14eb9c` · created 2026-11-18T14:23:08 · duration 4.37 s · cost $0.0000
- embedding model: BAAI/bge-small-en-v1.5 · models: n/a
- prompt versions: n/a
- config: `{"name": "exp1-chunking-layout", "description": "Exp 1: layout-aware chunking (headings, tables as own chunks, context header). Index main.", "index_name": "main", "retrieval": {"mode": "hybrid"}, "qa": {}, "extraction": {}, "agent": {}}`

## Retrieval

| metric | value [95% CI] |
|---|---|
| recall_at_1 | 0.622 [0.461, 0.759] (n=37) |
| recall_at_3 | 0.730 [0.570, 0.846] (n=37) |
| recall_at_5 | 0.865 [0.720, 0.941] (n=37) |
| recall_at_10 | 0.892 [0.753, 0.957] (n=37) |
| mrr | 0.710 (n=37) |

| type | n | recall@5 | mrr |
|---|---|---|---|
| cross_doc | 6 | 0.667 [0.300, 0.903] (n=6) | 0.435 |
| factual | 14 | 0.857 [0.601, 0.960] (n=14) | 0.821 |
| injection | 2 | 1.000 [0.342, 1.000] (n=2) | 1.000 |
| open | 4 | 1.000 [0.510, 1.000] (n=4) | 0.475 |
| revision | 3 | 1.000 [0.439, 1.000] (n=3) | 0.833 |
| table_lookup | 8 | 0.875 [0.529, 0.978] (n=8) | 0.719 |

## Ops

```json
{
 "retrieval": {
  "retrieval_latency_ms": {
   "n": 37,
   "p50": 23.0,
   "p95": 28.200000000000003,
   "mean": 23.216216216216218
  }
 }
}
```
