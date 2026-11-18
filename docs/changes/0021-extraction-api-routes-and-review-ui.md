# 3.3 Extraction API routes and review UI
## Summary
POST/GET/PATCH /extractions, approve/reject/push with RBAC (engineer edits; approver approves/pushes), consistent errors; /ui/review queue + detail page with value, evidence quote, page link, validation errors, editable fields, role-aware buttons
## Why
Part of milestone task 3.3 in SPECBRIDGE_SPEC.md Section 13.
## Changes (files/modules)
specbridge/api/routers/extractions.py specbridge/api/routers/ui.py specbridge/ui/templates/review*.html tests/integration/test_api_extractions.py
## How it was tested (commands + results)
integration test_api_extractions 4 passed: role matrix incl. audited denials, push exactly once, PATCH revalidation, push failure then retry, UI review flow
## Eval impact (baseline run id → new run id, deltas) or "n/a"
n/a
## Risks / follow-ups
none known
## Self-review checklist
- [x] tests added/updated   - [x] types pass   - [x] lint passes
- [x] no secrets            - [x] logs added for new code paths
- [x] docs updated          - [x] error handling covers failure modes
