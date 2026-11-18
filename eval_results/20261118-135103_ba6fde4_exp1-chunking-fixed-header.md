# Eval run `20261118-135103_ba6fde4_exp1-chunking-fixed-header`

- suites: retrieval · split: **dev** · provider: fake
- git: `ba6fde4` · created 2026-11-18T13:51:03 · duration 1.3 s · cost $0.0000
- embedding model: BAAI/bge-small-en-v1.5 · models: n/a
- prompt versions: n/a
- config: `{"name": "exp1-chunking-fixed-header", "description": "Exp 1b: fixed ~300-token chunks WITH the context header, to separate the effect of the header from the effect of layout-aware chunk boundaries. Index exp_fixed_hdr.", "index_name": "exp_fixed_hdr", "retrieval": {"mode": "hybrid"}, "qa": {}, "extraction": {}, "agent": {}}`

## Retrieval

| metric | value [95% CI] |
|---|---|
| recall_at_1 | 0.607 [0.476, 0.724] (n=56) |
| recall_at_3 | 0.732 [0.604, 0.830] (n=56) |
| recall_at_5 | 0.857 [0.743, 0.926] (n=56) |
| recall_at_10 | 0.946 [0.854, 0.982] (n=56) |
| mrr | 0.704 (n=56) |

| type | n | recall@5 | mrr |
|---|---|---|---|
| cross_doc | 9 | 0.778 [0.453, 0.937] (n=9) | 0.515 |
| factual | 21 | 0.714 [0.500, 0.862] (n=21) | 0.501 |
| injection | 3 | 1.000 [0.439, 1.000] (n=3) | 0.750 |
| open | 6 | 1.000 [0.610, 1.000] (n=6) | 1.000 |
| revision | 5 | 1.000 [0.566, 1.000] (n=5) | 0.900 |
| table_lookup | 12 | 1.000 [0.757, 1.000] (n=12) | 0.958 |

## Ops

```json
{
 "retrieval": {
  "retrieval_latency_ms": {
   "n": 56,
   "p50": 22.5,
   "p95": 27.25,
   "mean": 22.214285714285715
  }
 }
}
```
