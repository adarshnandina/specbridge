# 1.4 ERP mock service, seed, fault injection
## Summary
Separate FastAPI+SQLite mock ERP: parts, change requests, mandatory Idempotency-Key (replay same body, 409 on different body), fault injection (failure rate, fail first N writes, latency) via env and /_admin/faults, seed from synthetic ground truth, structured request logs
## Why
Part of milestone task 1.4 in SPECBRIDGE_SPEC.md Section 13.
## Changes (files/modules)
erp_mock/* tests/unit/test_erp_mock.py
## How it was tested (commands + results)
tests/unit/test_erp_mock.py 6 passed
## Eval impact (baseline run id → new run id, deltas) or "n/a"
n/a
## Risks / follow-ups
none known
## Self-review checklist
- [x] tests added/updated   - [x] types pass   - [x] lint passes
- [x] no secrets            - [x] logs added for new code paths
- [x] docs updated          - [x] error handling covers failure modes
