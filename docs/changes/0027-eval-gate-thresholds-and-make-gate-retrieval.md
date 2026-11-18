# 5.1 Eval gate, thresholds and make gate-retrieval
## Summary
eval/thresholds.yaml per spec (+ a latency noise floor); 'specbridge eval gate' compares candidate vs baseline (recall@5, MRR, QA accuracy/citation precision/abstention recall, extraction micro-F1, p95 latency, cost per 100 queries, agent safety scenarios), refuses incomparable runs (split or relevant dataset hash mismatch), exits 1 on regressions and 2 on errors; Makefile gate-retrieval uses the latest 'ci'-tagged run
## Why
Part of milestone task 5.1 in SPECBRIDGE_SPEC.md Section 13.
## Changes (files/modules)
specbridge/eval/gate.py eval/thresholds.yaml experiments/deliberate-regression-keyword.yaml specbridge/eval/datasets.py specbridge/cli.py Makefile tests/unit/test_gate.py
## How it was tested (commands + results)
unit test_gate 21 passed (every threshold boundary, improvements never fail, noise floor, suite filter, incomparable runs, CLI exit codes 0/1/2)
## Eval impact (baseline run id → new run id, deltas) or "n/a"
Deliberate regression proof: baseline 20261118-132236_7ca7287_initial-retrieval vs keyword-only run 20261118-134429_9ae7ca4_deliberate-regression (dev): recall@5 0.911 -> 0.536, MRR 0.684 -> 0.315, gate exit code 1. Clean re-run 20261118-134352_9ae7ca4_ci: gate PASSED (identical metrics)
## Risks / follow-ups
none known
## Self-review checklist
- [x] tests added/updated   - [x] types pass   - [x] lint passes
- [x] no secrets            - [x] logs added for new code paths
- [x] docs updated          - [x] error handling covers failure modes
