# Eval run `20261118-134610_ba6fde4_exp1-chunking-layout`

- suites: retrieval · split: **dev** · provider: fake
- git: `ba6fde4` · created 2026-11-18T13:46:10 · duration 4.18 s · cost $0.0000
- embedding model: BAAI/bge-small-en-v1.5 · models: n/a
- prompt versions: n/a
- config: `{"name": "exp1-chunking-layout", "description": "Exp 1: layout-aware chunking (headings, tables as own chunks, context header). Index main.", "index_name": "main", "retrieval": {"mode": "hybrid"}, "qa": {}, "extraction": {}, "agent": {}}`

## Retrieval

| metric | value [95% CI] |
|---|---|
| recall_at_1 | 0.554 [0.424, 0.676] (n=56) |
| recall_at_3 | 0.804 [0.682, 0.887] (n=56) |
| recall_at_5 | 0.911 [0.807, 0.961] (n=56) |
| recall_at_10 | 0.929 [0.830, 0.972] (n=56) |
| mrr | 0.684 (n=56) |

| type | n | recall@5 | mrr |
|---|---|---|---|
| cross_doc | 9 | 0.889 [0.565, 0.980] (n=9) | 0.760 |
| factual | 21 | 0.857 [0.654, 0.950] (n=21) | 0.591 |
| injection | 3 | 1.000 [0.439, 1.000] (n=3) | 0.778 |
| open | 6 | 1.000 [0.610, 1.000] (n=6) | 0.478 |
| revision | 5 | 0.800 [0.376, 0.964] (n=5) | 0.640 |
| table_lookup | 12 | 1.000 [0.757, 1.000] (n=12) | 0.889 |

## Ops

```json
{
 "retrieval": {
  "retrieval_latency_ms": {
   "n": 56,
   "p50": 25.0,
   "p95": 31.25,
   "mean": 25.107142857142858
  }
 }
}
```
