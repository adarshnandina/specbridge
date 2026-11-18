# 4.4 Agent scenario eval suite
## Summary
All scenarios (14 required + 1 extra: lost responses then retry) executed through the real HTTP API against a seeded environment in an ephemeral database; per-scenario expectations plus global invariants (ERP change requests == DONE runs, DONE only with an approved approval); safety scenarios S05,S06,S07,S10,S11,S12 reported separately; wired into 'specbridge eval run --suite agent'
## Why
Part of milestone task 4.4 in SPECBRIDGE_SPEC.md Section 13.
## Changes (files/modules)
specbridge/agent/{scenarios,eval_suite}.py specbridge/db/admin.py specbridge/db/session.py eval/datasets/agent_scenarios.yaml eval_results/*agent-scenarios-fake.*
## How it was tested (commands + results)
integration test_eval_run agent suite (hermetic, DB dropped afterwards); test_agent_scenarios 18
## Eval impact (baseline run id → new run id, deltas) or "n/a"
Run 20261118-134227_d77cbfa_agent-scenarios-fake (fake provider): 15/15 scenarios pass, 6/6 safety scenarios pass. Live-LLM agent run: blocked: needs API key
## Risks / follow-ups
none known
## Self-review checklist
- [x] tests added/updated   - [x] types pass   - [x] lint passes
- [x] no secrets            - [x] logs added for new code paths
- [x] docs updated          - [x] error handling covers failure modes
