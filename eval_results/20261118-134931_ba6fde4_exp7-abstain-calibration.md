# Eval run `20261118-134931_ba6fde4_exp7-abstain-calibration`

- suites: calibration · split: **test** · provider: fake
- git: `ba6fde4` · created 2026-11-18T13:49:31 · duration 1.15 s · cost $0.0000
- embedding model: BAAI/bge-small-en-v1.5 · models: n/a
- prompt versions: n/a
- config: `{"name": "exp7-abstain-calibration", "description": "Exp 7: sweep ABSTAIN_MIN_SCORE on the dev split (retrieval score gate, no LLM).", "index_name": "main", "retrieval": {"mode": "hybrid"}, "qa": {}, "extraction": {}, "agent": {}}`
- note: calibrated on the retrieval score only; the LLM's own answerable flag is a second, independent abstention mechanism

## Abstention calibration

- criterion: largest threshold with over-abstention on answerable questions <= 5%
- recommended threshold: **0.63**
- at that threshold: precision 0.667 [0.208, 0.939] (n=3), recall 0.333 [0.097, 0.700] (n=6), over-abstention 0.027 [0.005, 0.138] (n=37)
- mean top similarity: answerable 0.716 (n=37), unanswerable 0.675 (n=6)

| threshold | abstained | precision | recall | over-abstention |
|---|---|---|---|---|
| 0.30 | 0 | n/a | 0.000 [0.000, 0.390] (n=6) | 0.000 [0.000, 0.094] (n=37) |
| 0.35 | 0 | n/a | 0.000 [0.000, 0.390] (n=6) | 0.000 [0.000, 0.094] (n=37) |
| 0.40 | 0 | n/a | 0.000 [0.000, 0.390] (n=6) | 0.000 [0.000, 0.094] (n=37) |
| 0.45 | 0 | n/a | 0.000 [0.000, 0.390] (n=6) | 0.000 [0.000, 0.094] (n=37) |
| 0.50 | 0 | n/a | 0.000 [0.000, 0.390] (n=6) | 0.000 [0.000, 0.094] (n=37) |
| 0.55 | 0 | n/a | 0.000 [0.000, 0.390] (n=6) | 0.000 [0.000, 0.094] (n=37) |
| 0.60 | 1 | 0.000 [0.000, 0.793] (n=1) | 0.000 [0.000, 0.390] (n=6) | 0.027 [0.005, 0.138] (n=37) |
| 0.65 | 7 | 0.286 [0.082, 0.641] (n=7) | 0.333 [0.097, 0.700] (n=6) | 0.135 [0.059, 0.280] (n=37) |
| 0.70 | 20 | 0.250 [0.112, 0.469] (n=20) | 0.833 [0.436, 0.970] (n=6) | 0.405 [0.264, 0.565] (n=37) |
| 0.75 | 32 | 0.188 [0.089, 0.353] (n=32) | 1.000 [0.610, 1.000] (n=6) | 0.703 [0.542, 0.825] (n=37) |
| 0.80 | 40 | 0.150 [0.071, 0.291] (n=40) | 1.000 [0.610, 1.000] (n=6) | 0.919 [0.787, 0.972] (n=37) |
| 0.85 | 43 | 0.140 [0.066, 0.273] (n=43) | 1.000 [0.610, 1.000] (n=6) | 1.000 [0.906, 1.000] (n=37) |
| 0.90 | 43 | 0.140 [0.066, 0.273] (n=43) | 1.000 [0.610, 1.000] (n=6) | 1.000 [0.906, 1.000] (n=37) |

## Ops

```json
{
 "calibration": {
  "retrieval_latency_ms": {
   "n": 43,
   "p50": 25.0,
   "p95": 29.0,
   "mean": 25.488372093023255
  }
 }
}
```
