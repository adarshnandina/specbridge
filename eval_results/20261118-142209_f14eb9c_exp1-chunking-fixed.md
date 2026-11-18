# Eval run `20261118-142209_f14eb9c_exp1-chunking-fixed`

- suites: retrieval · split: **dev** · provider: fake
- git: `f14eb9c` · created 2026-11-18T14:22:09 · duration 1.52 s · cost $0.0000
- embedding model: BAAI/bge-small-en-v1.5 · models: n/a
- prompt versions: n/a
- config: `{"name": "exp1-chunking-fixed", "description": "Exp 1: fixed ~300-token chunks with 50 overlap, no context header. Index exp_fixed.", "index_name": "exp_fixed", "retrieval": {"mode": "hybrid"}, "qa": {}, "extraction": {}, "agent": {}}`

## Retrieval

| metric | value [95% CI] |
|---|---|
| recall_at_1 | 0.411 [0.292, 0.541] (n=56) |
| recall_at_3 | 0.571 [0.441, 0.692] (n=56) |
| recall_at_5 | 0.679 [0.548, 0.786] (n=56) |
| recall_at_10 | 0.786 [0.662, 0.873] (n=56) |
| mrr | 0.521 (n=56) |

| type | n | recall@5 | mrr |
|---|---|---|---|
| cross_doc | 9 | 0.889 [0.565, 0.980] (n=9) | 0.454 |
| factual | 21 | 0.476 [0.283, 0.676] (n=21) | 0.352 |
| injection | 3 | 1.000 [0.439, 1.000] (n=3) | 0.778 |
| open | 6 | 0.833 [0.436, 0.970] (n=6) | 0.750 |
| revision | 5 | 0.800 [0.376, 0.964] (n=5) | 0.829 |
| table_lookup | 12 | 0.667 [0.391, 0.862] (n=12) | 0.559 |

## Ops

```json
{
 "retrieval": {
  "retrieval_latency_ms": {
   "n": 56,
   "p50": 26.0,
   "p95": 30.25,
   "mean": 25.982142857142858
  }
 }
}
```
