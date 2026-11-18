# Eval run `20261118-134614_ba6fde4_exp1-chunking-fixed`

- suites: retrieval · split: **dev** · provider: fake
- git: `ba6fde4` · created 2026-11-18T13:46:14 · duration 1.47 s · cost $0.0000
- embedding model: BAAI/bge-small-en-v1.5 · models: n/a
- prompt versions: n/a
- config: `{"name": "exp1-chunking-fixed", "description": "Exp 1: fixed ~300-token chunks with 50 overlap, no context header. Index exp_fixed.", "index_name": "exp_fixed", "retrieval": {"mode": "hybrid"}, "qa": {}, "extraction": {}, "agent": {}}`

## Retrieval

| metric | value [95% CI] |
|---|---|
| recall_at_1 | 0.393 [0.276, 0.524] (n=56) |
| recall_at_3 | 0.554 [0.424, 0.676] (n=56) |
| recall_at_5 | 0.643 [0.512, 0.755] (n=56) |
| recall_at_10 | 0.786 [0.662, 0.873] (n=56) |
| mrr | 0.502 (n=56) |

| type | n | recall@5 | mrr |
|---|---|---|---|
| cross_doc | 9 | 0.778 [0.453, 0.937] (n=9) | 0.500 |
| factual | 21 | 0.429 [0.245, 0.634] (n=21) | 0.355 |
| injection | 3 | 1.000 [0.439, 1.000] (n=3) | 0.750 |
| open | 6 | 0.833 [0.436, 0.970] (n=6) | 0.722 |
| revision | 5 | 0.800 [0.376, 0.964] (n=5) | 0.733 |
| table_lookup | 12 | 0.667 [0.391, 0.862] (n=12) | 0.493 |

## Ops

```json
{
 "retrieval": {
  "retrieval_latency_ms": {
   "n": 56,
   "p50": 25.0,
   "p95": 28.25,
   "mean": 25.142857142857142
  }
 }
}
```
