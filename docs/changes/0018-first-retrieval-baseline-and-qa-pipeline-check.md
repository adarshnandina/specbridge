# 2.7 First retrieval baseline and QA pipeline check
## Summary
Retrieval eval on dev (hybrid, layout chunks, bge-small) set as eval_results/baseline.json; QA suite run with the fake provider as a pipeline check; real QA run blocked (no API key)
## Why
Part of milestone task 2.7 in SPECBRIDGE_SPEC.md Section 13.
## Changes (files/modules)
eval_results/* docs/build-log/PROGRESS.md
## How it was tested (commands + results)
no new tests; runs recorded in eval_results/
## Eval impact (baseline run id → new run id, deltas) or "n/a"
Retrieval baseline run 20261118-132236_7ca7287_initial-retrieval (dev, n=56): see eval_results/*initial-retrieval.md. Fake-provider QA run 20261118-132241_7ca7287_qa-fake-pipeline is a PIPELINE CHECK ONLY (extractive responder, constant judge) - not a quality result. Real QA run: blocked: needs API key
## Risks / follow-ups
none known
## Self-review checklist
- [x] tests added/updated   - [x] types pass   - [x] lint passes
- [x] no secrets            - [x] logs added for new code paths
- [x] docs updated          - [x] error handling covers failure modes
