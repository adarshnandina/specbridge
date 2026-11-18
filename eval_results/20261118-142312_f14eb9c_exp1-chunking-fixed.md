# Eval run `20261118-142312_f14eb9c_exp1-chunking-fixed`

- suites: retrieval · split: **test** · provider: fake
- git: `f14eb9c` · created 2026-11-18T14:23:12 · duration 0.9 s · cost $0.0000
- embedding model: BAAI/bge-small-en-v1.5 · models: n/a
- prompt versions: n/a
- config: `{"name": "exp1-chunking-fixed", "description": "Exp 1: fixed ~300-token chunks with 50 overlap, no context header. Index exp_fixed.", "index_name": "exp_fixed", "retrieval": {"mode": "hybrid"}, "qa": {}, "extraction": {}, "agent": {}}`

## Retrieval

| metric | value [95% CI] |
|---|---|
| recall_at_1 | 0.459 [0.310, 0.616] (n=37) |
| recall_at_3 | 0.568 [0.409, 0.713] (n=37) |
| recall_at_5 | 0.703 [0.542, 0.825] (n=37) |
| recall_at_10 | 0.784 [0.628, 0.886] (n=37) |
| mrr | 0.545 (n=37) |

| type | n | recall@5 | mrr |
|---|---|---|---|
| cross_doc | 6 | 0.667 [0.300, 0.903] (n=6) | 0.550 |
| factual | 14 | 0.714 [0.454, 0.883] (n=14) | 0.524 |
| injection | 2 | 1.000 [0.342, 1.000] (n=2) | 0.750 |
| open | 4 | 0.250 [0.046, 0.699] (n=4) | 0.250 |
| revision | 3 | 1.000 [0.439, 1.000] (n=3) | 0.778 |
| table_lookup | 8 | 0.750 [0.409, 0.928] (n=8) | 0.585 |

## Ops

```json
{
 "retrieval": {
  "retrieval_latency_ms": {
   "n": 37,
   "p50": 23.0,
   "p95": 28.0,
   "mean": 23.16216216216216
  }
 }
}
```
