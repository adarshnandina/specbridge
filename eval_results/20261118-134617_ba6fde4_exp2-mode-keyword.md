# Eval run `20261118-134617_ba6fde4_exp2-mode-keyword`

- suites: retrieval · split: **dev** · provider: fake
- git: `ba6fde4` · created 2026-11-18T13:46:17 · duration 1.44 s · cost $0.0000
- embedding model: BAAI/bge-small-en-v1.5 · models: n/a
- prompt versions: n/a
- config: `{"name": "exp2-mode-keyword", "description": "Exp 2: keyword (Postgres full text) only.", "index_name": "main", "retrieval": {"mode": "keyword"}, "qa": {}, "extraction": {}, "agent": {}}`

## Retrieval

| metric | value [95% CI] |
|---|---|
| recall_at_1 | 0.214 [0.127, 0.338] (n=56) |
| recall_at_3 | 0.339 [0.229, 0.470] (n=56) |
| recall_at_5 | 0.536 [0.407, 0.660] (n=56) |
| recall_at_10 | 0.643 [0.512, 0.755] (n=56) |
| mrr | 0.315 (n=56) |

| type | n | recall@5 | mrr |
|---|---|---|---|
| cross_doc | 9 | 0.667 [0.354, 0.879] (n=9) | 0.387 |
| factual | 21 | 0.333 [0.172, 0.546] (n=21) | 0.341 |
| injection | 3 | 0.667 [0.208, 0.939] (n=3) | 0.417 |
| open | 6 | 0.667 [0.300, 0.903] (n=6) | 0.177 |
| revision | 5 | 0.400 [0.118, 0.769] (n=5) | 0.433 |
| table_lookup | 12 | 0.750 [0.468, 0.911] (n=12) | 0.211 |

## Ops

```json
{
 "retrieval": {
  "retrieval_latency_ms": {
   "n": 56,
   "p50": 25.0,
   "p95": 28.0,
   "mean": 24.589285714285715
  }
 }
}
```
