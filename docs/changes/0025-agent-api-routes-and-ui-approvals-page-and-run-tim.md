# 4.3 Agent API routes and UI: approvals page and run timeline
## Summary
POST/GET /agent/runs, steps, retry; GET /approvals, approve/reject; UI /ui/runs (start form + list), /ui/runs/{id} timeline with tool calls, status, latency, outputs and state transitions, /ui/approvals with evidence quotes and role-aware approve/reject, retry button for failed commits
## Why
Part of milestone task 4.3 in SPECBRIDGE_SPEC.md Section 13.
## Changes (files/modules)
specbridge/api/routers/agent.py specbridge/api/routers/ui.py specbridge/ui/templates/{approvals,runs,run_detail}.html tests/integration/test_api_agent_ui.py
## How it was tested (commands + results)
integration test_api_agent_ui 4 passed (RBAC incl. viewer 403, engineer cannot approve, requester-approver four-eyes 403, double decision 409, failed commit then retry endpoint, UI flow)
## Eval impact (baseline run id → new run id, deltas) or "n/a"
n/a
## Risks / follow-ups
none known
## Self-review checklist
- [x] tests added/updated   - [x] types pass   - [x] lint passes
- [x] no secrets            - [x] logs added for new code paths
- [x] docs updated          - [x] error handling covers failure modes
