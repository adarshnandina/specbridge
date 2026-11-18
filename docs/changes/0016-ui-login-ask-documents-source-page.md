# 2.5 UI: login, ask, documents, source page
## Summary
Jinja2 server-rendered UI: /ui/login (API key -> signed httponly SameSite=Strict cookie holding user+role), /ui/ask with numbered citations linking to /ui/source (quote + highlighted page image), /ui/documents; same RBAC; cookie-auth page image route; plain CSS
## Why
Part of milestone task 2.5 in SPECBRIDGE_SPEC.md Section 13.
## Changes (files/modules)
specbridge/api/routers/ui.py specbridge/ui/* tests/integration/test_ui.py
## How it was tested (commands + results)
integration test_ui 7 passed (redirect when logged out, bad key, forged cookie, cookie flags, full ask->source->PNG flow, HTML escaping, logout, static). Manual check: real uvicorn run against the ingested dev DB, highlighted page PNG inspected visually
## Eval impact (baseline run id → new run id, deltas) or "n/a"
n/a
## Risks / follow-ups
none known
## Self-review checklist
- [x] tests added/updated   - [x] types pass   - [x] lint passes
- [x] no secrets            - [x] logs added for new code paths
- [x] docs updated          - [x] error handling covers failure modes
