# 5.3 Final defaults confirmed; full dev baseline and test-split report
## Summary
Defaults confirmed unchanged by the experiments. Full evaluation (retrieval, QA, extraction, agent; fake provider for LLM suites) run on dev and set as eval_results/baseline.json (the gate reference), and on test as the final report; make eval-retrieval gate-retrieval passes against the new baseline
## Why
Part of milestone task 5.3 in SPECBRIDGE_SPEC.md Section 13.
## Changes (files/modules)
eval_results/baseline.json eval_results/*baseline-dev-all.* eval_results/*final-test-all.* docs/decisions/DECISION_LOG.md
## How it was tested (commands + results)
n/a (evaluation runs); gate PASSED for the baseline run itself and for a fresh 'ci' retrieval run
## Eval impact (baseline run id → new run id, deltas) or "n/a"
Baseline (dev, set via 'eval set-baseline'): 20261118-135200_e64a52b_baseline-dev-all. Final test-split report: 20261118-135217_e64a52b_final-test-all (retrieval recall@5 0.865 n=37; agent 15/15 scenarios, 6/6 safety; QA/extraction numbers are fake-provider pipeline checks, NOT model quality). Real-model QA/extraction/agent runs: blocked: needs API key
## Risks / follow-ups
none known
## Self-review checklist
- [x] tests added/updated   - [x] types pass   - [x] lint passes
- [x] no secrets            - [x] logs added for new code paths
- [x] docs updated          - [x] error handling covers failure modes
