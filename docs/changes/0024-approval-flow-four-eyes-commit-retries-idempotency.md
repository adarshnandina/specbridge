# 4.2 Approval flow, four-eyes, commit retries/idempotency, explicit resume
## Summary
approvals row created in AWAITING_APPROVAL (idempotent); POST /approvals/{id}/approve|reject; four-eyes rule (requester cannot decide, denial audited in its own transaction); COMMITTING uses idempotency key = run id with tenacity retries (3 attempts) -> FAILED(retryable) -> POST /agent/runs/{id}/retry; resume after crash via AgentRunner.resume; ERP fault 'lose_response_first_n' (write executes, response lost) added to prove idempotency
## Why
Part of milestone task 4.2 in SPECBRIDGE_SPEC.md Section 13.
## Changes (files/modules)
specbridge/api/routers/agent.py specbridge/agent/runner.py erp_mock/* specbridge/audit.py
## How it was tested (commands + results)
integration test_agent_runner approval/four-eyes/double-decision + resume tests; scenario S08/S09/S13/S15. Mutation checks performed manually: removing allowlist entry, four-eyes check, discontinued filter, or stable idempotency key each makes a scenario FAIL (see journal)
## Eval impact (baseline run id → new run id, deltas) or "n/a"
n/a
## Risks / follow-ups
none known
## Self-review checklist
- [x] tests added/updated   - [x] types pass   - [x] lint passes
- [x] no secrets            - [x] logs added for new code paths
- [x] docs updated          - [x] error handling covers failure modes
