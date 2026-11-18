# Eval run `20261118-135105_ba6fde4_exp1-chunking-fixed-header`

- suites: retrieval · split: **test** · provider: fake
- git: `ba6fde4` · created 2026-11-18T13:51:05 · duration 3.55 s · cost $0.0000
- embedding model: BAAI/bge-small-en-v1.5 · models: n/a
- prompt versions: n/a
- config: `{"name": "exp1-chunking-fixed-header", "description": "Exp 1b: fixed ~300-token chunks WITH the context header, to separate the effect of the header from the effect of layout-aware chunk boundaries. Index exp_fixed_hdr.", "index_name": "exp_fixed_hdr", "retrieval": {"mode": "hybrid"}, "qa": {}, "extraction": {}, "agent": {}}`

## Retrieval

| metric | value [95% CI] |
|---|---|
| recall_at_1 | 0.595 [0.435, 0.737] (n=37) |
| recall_at_3 | 0.811 [0.658, 0.905] (n=37) |
| recall_at_5 | 0.865 [0.720, 0.941] (n=37) |
| recall_at_10 | 0.946 [0.823, 0.985] (n=37) |
| mrr | 0.707 (n=37) |

| type | n | recall@5 | mrr |
|---|---|---|---|
| cross_doc | 6 | 0.500 [0.188, 0.812] (n=6) | 0.540 |
| factual | 14 | 0.857 [0.601, 0.960] (n=14) | 0.674 |
| injection | 2 | 1.000 [0.342, 1.000] (n=2) | 1.000 |
| open | 4 | 1.000 [0.510, 1.000] (n=4) | 0.875 |
| revision | 3 | 1.000 [0.439, 1.000] (n=3) | 0.611 |
| table_lookup | 8 | 1.000 [0.676, 1.000] (n=8) | 0.771 |

## Ops

```json
{
 "retrieval": {
  "retrieval_latency_ms": {
   "n": 37,
   "p50": 20.0,
   "p95": 26.200000000000003,
   "mean": 21.2972972972973
  }
 }
}
```
