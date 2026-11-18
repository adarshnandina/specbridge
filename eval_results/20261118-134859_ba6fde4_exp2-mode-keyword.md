# Eval run `20261118-134859_ba6fde4_exp2-mode-keyword`

- suites: retrieval · split: **test** · provider: fake
- git: `ba6fde4` · created 2026-11-18T13:48:59 · duration 0.91 s · cost $0.0000
- embedding model: BAAI/bge-small-en-v1.5 · models: n/a
- prompt versions: n/a
- config: `{"name": "exp2-mode-keyword", "description": "Exp 2: keyword (Postgres full text) only.", "index_name": "main", "retrieval": {"mode": "keyword"}, "qa": {}, "extraction": {}, "agent": {}}`

## Retrieval

| metric | value [95% CI] |
|---|---|
| recall_at_1 | 0.216 [0.114, 0.372] (n=37) |
| recall_at_3 | 0.351 [0.218, 0.512] (n=37) |
| recall_at_5 | 0.514 [0.359, 0.665] (n=37) |
| recall_at_10 | 0.703 [0.542, 0.825] (n=37) |
| mrr | 0.336 (n=37) |

| type | n | recall@5 | mrr |
|---|---|---|---|
| cross_doc | 6 | 0.333 [0.097, 0.700] (n=6) | 0.132 |
| factual | 14 | 0.500 [0.268, 0.732] (n=14) | 0.304 |
| injection | 2 | 1.000 [0.342, 1.000] (n=2) | 0.667 |
| open | 4 | 0.500 [0.150, 0.850] (n=4) | 0.211 |
| revision | 3 | 0.333 [0.061, 0.792] (n=3) | 0.370 |
| table_lookup | 8 | 0.625 [0.306, 0.863] (n=8) | 0.512 |

## Ops

```json
{
 "retrieval": {
  "retrieval_latency_ms": {
   "n": 37,
   "p50": 23.0,
   "p95": 26.200000000000003,
   "mean": 23.18918918918919
  }
 }
}
```
