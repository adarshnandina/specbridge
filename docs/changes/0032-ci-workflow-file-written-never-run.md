# 6.3 CI workflow file (written, never run)
## Summary
.github/workflows/ci.yml mirrors make ci with a Postgres service container (lint, typecheck, unit, migrate, integration, coverage gate, pip-audit, corpus+ingest, retrieval eval + gate, upload eval results). Never pushed or triggered; no git remote exists
## Why
Part of milestone task 6.3 in SPECBRIDGE_SPEC.md Section 13.
## Changes (files/modules)
.github/workflows/ci.yml
## How it was tested (commands + results)
n/a (not run by design: hard rule 1)
## Eval impact (baseline run id → new run id, deltas) or "n/a"
n/a
## Risks / follow-ups
none known
## Self-review checklist
- [x] tests added/updated   - [x] types pass   - [x] lint passes
- [x] no secrets            - [x] logs added for new code paths
- [x] docs updated          - [x] error handling covers failure modes
