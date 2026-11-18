# 6.4 Documentation, ADRs, and gaps found while documenting
## Summary
README, ARCHITECTURE (Mermaid diagrams, security design, failure modes), EVALUATION, EXPERIMENTS, LIMITATIONS, DEPLOYMENT, RUNBOOK, API (real responses captured from the running stack), WALKTHROUGH, PROJECT_STORY and ADRs 0001-0009. Writing them against the real system exposed four gaps that were fixed: GET /audit (admin) was missing; judge_calibration.jsonl did not exist (20 programmatic candidates, empty human_score); the budget-remaining gauge was never set and log lines lacked request_id/actor/role outside requests; unpriced (e.g. Bedrock) models silently skipped accounting - now refused before the call, with an aliases map in config/pricing.yaml. make ci is now self-contained (db-up, migrate, corpus, ingest before the retrieval eval and gate)
## Why
Part of milestone task 6.4 in SPECBRIDGE_SPEC.md Section 13.
## Changes (files/modules)
README.md docs/*.md docs/decisions/*.md specbridge/api/routers/audit.py specbridge/llm/pricing.py specbridge/llm/usage.py specbridge/logging_setup.py corpus/synthetic/judge_calibration.py eval/datasets/judge_calibration.jsonl config/pricing.yaml Makefile
## How it was tested (commands + results)
integration test_audit_endpoint_admin_only_with_filters; unit test_observability (budget gauge, log fields, judge dataset), test_llm (unpriced model refused); validate-datasets OK
## Eval impact (baseline run id → new run id, deltas) or "n/a"
n/a
## Risks / follow-ups
none known
## Self-review checklist
- [x] tests added/updated   - [x] types pass   - [x] lint passes
- [x] no secrets            - [x] logs added for new code paths
- [x] docs updated          - [x] error handling covers failure modes
