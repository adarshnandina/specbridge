# 4.1 Agent state machine, tools, allowlists, limits
## Summary
Explicit persisted state machine (RECEIVED..DONE, REJECTED/FAILED/ESCALATED) with transition table; per-state tool allowlists (write tool only in COMMITTING and only with an approved approval row); deterministic search_parts via parameterised SQLAlchemy (category, temp range, voltage overlap, IP>=, constraints, ERP lifecycle exclusion, max 10); COMPARE loop with max 3 evidence calls, ranking validation (candidate whitelist, citation verification, uncited claims removed, escalate if no verified evidence); max 6 LLM calls; 120s step limit; untrusted evidence wrapped as data
## Why
Part of milestone task 4.1 in SPECBRIDGE_SPEC.md Section 13.
## Changes (files/modules)
specbridge/agent/{states,permissions,models,tools,runner,fake}.py specbridge/prompts/agent_*.md tests/unit/test_agent_units.py tests/integration/test_agent_runner.py
## How it was tested (commands + results)
unit test_agent_units 12; integration test_agent_runner 9 (write guard, step/audit persistence, evidence cap, LLM-call cap -> ESCALATED, hallucinated parts/uncited claims dropped, no-evidence escalation, step timeout, explicit resume)
## Eval impact (baseline run id → new run id, deltas) or "n/a"
n/a
## Risks / follow-ups
none known
## Self-review checklist
- [x] tests added/updated   - [x] types pass   - [x] lint passes
- [x] no secrets            - [x] logs added for new code paths
- [x] docs updated          - [x] error handling covers failure modes
