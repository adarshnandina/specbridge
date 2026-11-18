# 0006 - Evaluation strategy and gating

## Context
Changes to chunking, prompts or models must be judged on evidence, cheaply, and without fooling
ourselves on small samples.

## Decision
- Datasets are generated from ground truth where possible (correct by construction), split 60/40
  dev/test; tuning uses dev only, test is run once for confirmation.
- Retrieval evaluation needs no LLM, so it runs in `make ci` on every change; LLM suites run on
  demand (`make eval-all`) or with the fake provider (agent scenarios run in CI).
- Every metric reports n and a 95% Wilson interval; comparisons flag `significant` (disjoint CIs),
  `weak`, or `within noise`; improvements within noise are not claimed.
- `specbridge eval gate` compares a candidate to `eval_results/baseline.json` using
  `eval/thresholds.yaml` and exits 1 on regression. Runs are comparable only if the split and the
  datasets the suite depends on match. A latency noise floor (20 ms) prevents flaky failures on a
  ~25 ms stage.
- The baseline is the full **dev** run (so the CI gate never touches test); the test-split run is a
  separate final report.

## Consequences
- The gate was shown to catch a deliberate regression (keyword-only retrieval, `20261118-142214_f14eb9c_exp2-mode-keyword`:
  recall@5 0.875 -> 0.464, exit code 1) and to refuse incomparable runs (split, datasets, indexed corpus).
- A fresh checkout failed the gate (recall@5 0.84 vs 0.91): ties were broken by random UUIDs, so results depended on the
  ingest. Fixed with deterministic tie-breaks and corpus recording; everything was re-measured and re-baselined.
- Small sets mean wide intervals; many differences cannot be resolved (docs/EXPERIMENTS.md).
- The judge for open questions is uncalibrated until a human scores `judge_calibration.jsonl`.
