# 0.7 Auth, RBAC, audit
## Summary
API key store with constant-time compare, permission matrix, FastAPI require() dependency, append-only audit log, denials audited in separate transaction
## Why
Part of milestone task 0.7 in SPECBRIDGE_SPEC.md Section 13.
## Changes (files/modules)
specbridge/auth/* audit.py api/deps.py
## How it was tested (commands + results)
tests/unit/test_auth.py pass; integration test_audit_and_denied_survive
## Eval impact (baseline run id → new run id, deltas) or "n/a"
n/a
## Risks / follow-ups
none known
## Self-review checklist
- [x] tests added/updated   - [x] types pass   - [x] lint passes
- [x] no secrets            - [x] logs added for new code paths
- [x] docs updated          - [x] error handling covers failure modes
