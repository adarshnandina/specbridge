# 3.4 Extraction eval suite
## Summary
Suite scoring per-field and micro P/R/F1 (1% numeric tolerance, null handling, set comparison for lists), evidence validity rate, % auto-validated vs needing review, precision of validated records (doc-level and field-level), attempts, cost per document; synthetic labels + provisional real labels reported separately; config options model/retry/include_real for experiments; compact markdown report
## Why
Part of milestone task 3.4 in SPECBRIDGE_SPEC.md Section 13.
## Changes (files/modules)
specbridge/extraction/eval_suite.py specbridge/eval/runner.py tests/unit/test_extraction_eval.py tests/integration/test_eval_run.py eval_results/*extraction-fake-pipeline.*
## How it was tested (commands + results)
unit test_extraction_eval 4; integration test_eval_run 7 (adds extraction suite + config options)
## Eval impact (baseline run id → new run id, deltas) or "n/a"
Fake-provider extraction run 20261118-132949_2cf9cda_extraction-fake-pipeline (dev, 33 synthetic docs): PIPELINE CHECK ONLY - the 'model' is a rule-based regex extractor. Real extraction run: blocked: needs API key
## Risks / follow-ups
none known
## Self-review checklist
- [x] tests added/updated   - [x] types pass   - [x] lint passes
- [x] no secrets            - [x] logs added for new code paths
- [x] docs updated          - [x] error handling covers failure modes
