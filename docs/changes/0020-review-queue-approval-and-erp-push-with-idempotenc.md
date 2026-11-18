# 3.2 Review queue, approval and ERP push with idempotency
## Summary
ERP client (tenacity retries on 5xx/timeouts, mandatory idempotency keys); review service: audited field edits (old/new), re-validation on save, mark reviewed, approve (unreviewed pending items blocked), reject, push with key=sha256(extraction_id+schema_version) and retryable push_failed
## Why
Part of milestone task 3.2 in SPECBRIDGE_SPEC.md Section 13.
## Changes (files/modules)
specbridge/erp_client/client.py specbridge/extraction/review.py tests/integration/test_extraction_flow.py
## How it was tested (commands + results)
integration test_extraction_flow 7 passed: extract->validated, validation failure->review->edit->approve->push, edit type/unknown-field guards, reject/state guards, transient ERP failures -> exactly one ERP write, permanent failure -> push_failed -> retry -> exactly one write, audit order error then allowed
## Eval impact (baseline run id → new run id, deltas) or "n/a"
n/a
## Risks / follow-ups
none known
## Self-review checklist
- [x] tests added/updated   - [x] types pass   - [x] lint passes
- [x] no secrets            - [x] logs added for new code paths
- [x] docs updated          - [x] error handling covers failure modes
