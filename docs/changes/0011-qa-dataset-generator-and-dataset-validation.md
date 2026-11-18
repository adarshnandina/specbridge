# 1.3 QA dataset generator and dataset validation
## Summary
108 QA items generated programmatically from ground truth (factual 35, table_lookup 20, cross_doc 15, revision 8, unanswerable 15, injection 5, open 10), 60/40 dev/test; loader + validate_datasets()
## Why
Part of milestone task 1.3 in SPECBRIDGE_SPEC.md Section 13.
## Changes (files/modules)
corpus/synthetic/qa_dataset.py specbridge/eval/datasets.py eval/datasets/qa.jsonl tests/unit/test_datasets.py
## How it was tested (commands + results)
tests/unit/test_datasets.py 6 passed; validate_datasets() returns no problems
## Eval impact (baseline run id → new run id, deltas) or "n/a"
n/a
## Risks / follow-ups
none known
## Self-review checklist
- [x] tests added/updated   - [x] types pass   - [x] lint passes
- [x] no secrets            - [x] logs added for new code paths
- [x] docs updated          - [x] error handling covers failure modes
