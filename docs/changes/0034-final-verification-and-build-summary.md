# 6.5 Final verification and build summary
## Summary
Whole-build verification against Section 14. (1) Fresh clone -> cp .env.example .env -> make setup -> make ci exits 0: lint, mypy strict, 221 unit + 94 integration tests (Testcontainers), combined coverage 91% (>=80%), pip-audit clean, db-up + migrate + ingest of 60 documents, retrieval eval identical to the baseline (recall@5 0.875, MRR 0.722), gate PASSED. (2) docker compose down -v then up --build from empty volumes: db, erp-mock, api healthy, /ready 200 (database/embedding_model/erp ok), make test-e2e 3 passed. (3) UI ask -> highlighted source page, upload->query->highlighted PNG verified by integration and e2e tests. (4)-(6) abstention/injection metrics, extraction->review->approve->push exactly once, agent happy path only after approval by a different user, 15/15 scenarios and 6/6 safety scenarios. (7) llm_calls, request ids, audit log verified by tests. (8) eval_results/baseline.json = 20261118-142407_f14eb9c_baseline-dev-all; gate fails on 20261118-142214_f14eb9c_exp2-mode-keyword (exit 1). (9) all Section 12 docs exist; every run id mentioned in docs exists in eval_results/. (10) journal entry, change note and commit for every task; no git remote; .env never tracked. (11) see Deviations.
## Why
Part of milestone task 6.5 in SPECBRIDGE_SPEC.md Section 13.
## Changes (files/modules)
scripts/dev/render_docs.py scripts/dev/*.template.md docs/* README.md specbridge/retrieval/* specbridge/eval/{runner,gate,experiments}.py Makefile specbridge/config.py .env.example eval_results/*
## How it was tested (commands + results)
unit 221, integration 94, e2e 3 (against docker compose), coverage 91%
## Eval impact (baseline run id → new run id, deltas) or "n/a"
Baseline 20261118-142407_f14eb9c_baseline-dev-all (dev, gate reference); final test-split report 20261118-142424_f14eb9c_final-test-all. Retrieval dev recall@5 0.875 [0.76,0.94] n=56, test 0.892 n=37; agent 15/15 and safety 6/6; QA/extraction/judge numbers are FAKE-provider pipeline checks. First-pass experiment runs (pre-determinism) are kept but superseded
## Risks / follow-ups
none known
## Self-review checklist
- [x] tests added/updated   - [x] types pass   - [x] lint passes
- [x] no secrets            - [x] logs added for new code paths
- [x] docs updated          - [x] error handling covers failure modes
