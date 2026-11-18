# 1.1 Synthetic datasheet generator and ground truth
## Summary
Deterministic generator (seed 42): 3 fictional vendors, 45 parts + 5 rev1.1 + 1 prompt-injection datasheet = 51 PDFs in 4 layout families with format variety; ground truth with per-field evidence pages, lifecycle, replacement candidates; shared candidate rule in specbridge/extraction/fields.py
## Why
Part of milestone task 1.1 in SPECBRIDGE_SPEC.md Section 13.
## Changes (files/modules)
corpus/synthetic/* specbridge/extraction/fields.py eval/datasets/extraction_synthetic.jsonl tests/unit/test_corpus.py
## How it was tested (commands + results)
tests/unit/test_corpus.py 8 passed (counts, determinism, revisions, scenario invariants, injection doc)
## Eval impact (baseline run id → new run id, deltas) or "n/a"
n/a
## Risks / follow-ups
none known
## Self-review checklist
- [x] tests added/updated   - [x] types pass   - [x] lint passes
- [x] no secrets            - [x] logs added for new code paths
- [x] docs updated          - [x] error handling covers failure modes
