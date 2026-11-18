# Eval run `20261118-134857_ba6fde4_exp1-chunking-fixed`

- suites: retrieval · split: **test** · provider: fake
- git: `ba6fde4` · created 2026-11-18T13:48:57 · duration 0.93 s · cost $0.0000
- embedding model: BAAI/bge-small-en-v1.5 · models: n/a
- prompt versions: n/a
- config: `{"name": "exp1-chunking-fixed", "description": "Exp 1: fixed ~300-token chunks with 50 overlap, no context header. Index exp_fixed.", "index_name": "exp_fixed", "retrieval": {"mode": "hybrid"}, "qa": {}, "extraction": {}, "agent": {}}`

## Retrieval

| metric | value [95% CI] |
|---|---|
| recall_at_1 | 0.432 [0.287, 0.591] (n=37) |
| recall_at_3 | 0.541 [0.384, 0.690] (n=37) |
| recall_at_5 | 0.676 [0.515, 0.804] (n=37) |
| recall_at_10 | 0.838 [0.689, 0.923] (n=37) |
| mrr | 0.536 (n=37) |

| type | n | recall@5 | mrr |
|---|---|---|---|
| cross_doc | 6 | 0.667 [0.300, 0.903] (n=6) | 0.533 |
| factual | 14 | 0.643 [0.388, 0.837] (n=14) | 0.526 |
| injection | 2 | 1.000 [0.342, 1.000] (n=2) | 0.750 |
| open | 4 | 0.250 [0.046, 0.699] (n=4) | 0.333 |
| revision | 3 | 1.000 [0.439, 1.000] (n=3) | 0.778 |
| table_lookup | 8 | 0.750 [0.409, 0.928] (n=8) | 0.512 |

## Ops

```json
{
 "retrieval": {
  "retrieval_latency_ms": {
   "n": 37,
   "p50": 24.0,
   "p95": 29.0,
   "mean": 23.83783783783784
  }
 }
}
```
