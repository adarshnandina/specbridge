# Eval run `20261118-134707_ba6fde4_exp7-abstain-calibration`

- suites: calibration · split: **dev** · provider: fake
- git: `ba6fde4` · created 2026-11-18T13:47:07 · duration 1.75 s · cost $0.0000
- embedding model: BAAI/bge-small-en-v1.5 · models: n/a
- prompt versions: n/a
- config: `{"name": "exp7-abstain-calibration", "description": "Exp 7: sweep ABSTAIN_MIN_SCORE on the dev split (retrieval score gate, no LLM).", "index_name": "main", "retrieval": {"mode": "hybrid"}, "qa": {}, "extraction": {}, "agent": {}}`
- note: calibrated on the retrieval score only; the LLM's own answerable flag is a second, independent abstention mechanism

## Abstention calibration

- criterion: largest threshold with over-abstention on answerable questions <= 5%
- recommended threshold: **0.62**
- at that threshold: precision 0.500 [0.150, 0.850] (n=4), recall 0.222 [0.063, 0.547] (n=9), over-abstention 0.036 [0.010, 0.121] (n=56)
- mean top similarity: answerable 0.706 (n=56), unanswerable 0.672 (n=9)

| threshold | abstained | precision | recall | over-abstention |
|---|---|---|---|---|
| 0.30 | 0 | n/a | 0.000 [0.000, 0.299] (n=9) | 0.000 [0.000, 0.064] (n=56) |
| 0.35 | 0 | n/a | 0.000 [0.000, 0.299] (n=9) | 0.000 [0.000, 0.064] (n=56) |
| 0.40 | 0 | n/a | 0.000 [0.000, 0.299] (n=9) | 0.000 [0.000, 0.064] (n=56) |
| 0.45 | 0 | n/a | 0.000 [0.000, 0.299] (n=9) | 0.000 [0.000, 0.064] (n=56) |
| 0.50 | 0 | n/a | 0.000 [0.000, 0.299] (n=9) | 0.000 [0.000, 0.064] (n=56) |
| 0.55 | 0 | n/a | 0.000 [0.000, 0.299] (n=9) | 0.000 [0.000, 0.064] (n=56) |
| 0.60 | 2 | 1.000 [0.342, 1.000] (n=2) | 0.222 [0.063, 0.547] (n=9) | 0.000 [0.000, 0.064] (n=56) |
| 0.65 | 7 | 0.286 [0.082, 0.641] (n=7) | 0.222 [0.063, 0.547] (n=9) | 0.089 [0.039, 0.193] (n=56) |
| 0.70 | 30 | 0.167 [0.073, 0.336] (n=30) | 0.556 [0.267, 0.811] (n=9) | 0.446 [0.324, 0.576] (n=56) |
| 0.75 | 54 | 0.148 [0.077, 0.266] (n=54) | 0.889 [0.565, 0.980] (n=9) | 0.821 [0.702, 0.900] (n=56) |
| 0.80 | 65 | 0.138 [0.075, 0.243] (n=65) | 1.000 [0.701, 1.000] (n=9) | 1.000 [0.936, 1.000] (n=56) |
| 0.85 | 65 | 0.138 [0.075, 0.243] (n=65) | 1.000 [0.701, 1.000] (n=9) | 1.000 [0.936, 1.000] (n=56) |
| 0.90 | 65 | 0.138 [0.075, 0.243] (n=65) | 1.000 [0.701, 1.000] (n=9) | 1.000 [0.936, 1.000] (n=56) |

## Ops

```json
{
 "calibration": {
  "retrieval_latency_ms": {
   "n": 65,
   "p50": 26.0,
   "p95": 29.0,
   "mean": 25.861538461538462
  }
 }
}
```
