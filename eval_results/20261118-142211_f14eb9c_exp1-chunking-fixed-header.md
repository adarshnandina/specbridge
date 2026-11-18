# Eval run `20261118-142211_f14eb9c_exp1-chunking-fixed-header`

- suites: retrieval · split: **dev** · provider: fake
- git: `f14eb9c` · created 2026-11-18T14:22:11 · duration 1.57 s · cost $0.0000
- embedding model: BAAI/bge-small-en-v1.5 · models: n/a
- prompt versions: n/a
- config: `{"name": "exp1-chunking-fixed-header", "description": "Exp 1b: fixed ~300-token chunks WITH the context header, to separate the effect of the header from the effect of layout-aware chunk boundaries. Index exp_fixed_hdr.", "index_name": "exp_fixed_hdr", "retrieval": {"mode": "hybrid"}, "qa": {}, "extraction": {}, "agent": {}}`

## Retrieval

| metric | value [95% CI] |
|---|---|
| recall_at_1 | 0.571 [0.441, 0.692] (n=56) |
| recall_at_3 | 0.732 [0.604, 0.830] (n=56) |
| recall_at_5 | 0.893 [0.785, 0.950] (n=56) |
| recall_at_10 | 0.946 [0.854, 0.982] (n=56) |
| mrr | 0.684 (n=56) |

| type | n | recall@5 | mrr |
|---|---|---|---|
| cross_doc | 9 | 0.778 [0.453, 0.937] (n=9) | 0.368 |
| factual | 21 | 0.810 [0.600, 0.923] (n=21) | 0.516 |
| injection | 3 | 1.000 [0.439, 1.000] (n=3) | 0.778 |
| open | 6 | 1.000 [0.610, 1.000] (n=6) | 1.000 |
| revision | 5 | 1.000 [0.566, 1.000] (n=5) | 0.900 |
| table_lookup | 12 | 1.000 [0.757, 1.000] (n=12) | 0.944 |

## Ops

```json
{
 "retrieval": {
  "retrieval_latency_ms": {
   "n": 56,
   "p50": 27.0,
   "p95": 30.25,
   "mean": 26.857142857142858
  }
 }
}
```
