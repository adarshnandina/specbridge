# 6.2 Dockerfile, compose, prod compose, e2e tests, CLI resume/logs, storage paths
## Summary
Multi-stage non-root Dockerfile (uv, CPU-only torch on Linux, embedding model baked into the image, HEALTHCHECK, migrations in entrypoint); docker-compose with db, erp-mock (seeded once) and api with health-gated dependencies; docker-compose.prod.yml + Caddyfile (documentation only, never run); e2e tests against the running stack; 'specbridge agent resume|show' and 'specbridge logs tail --event'; PDF paths stored relative to DATA_DIR with fallback; Makefile coverage-check (unit+integration >= 80%)
## Why
Part of milestone task 6.2 in SPECBRIDGE_SPEC.md Section 13.
## Changes (files/modules)
docker/* docker-compose*.yml tests/e2e/test_e2e.py specbridge/cli.py specbridge/ingestion/{storage,pipeline}.py Makefile pyproject.toml uv.lock erp_mock/seed.py tests/unit/test_cli.py tests/unit/test_security.py tests/integration/test_foundations.py
## How it was tested (commands + results)
make test-e2e: 3 passed against 'docker compose up' (health/ready/metrics+auth, upload->query->highlighted PNG, agent happy path with approval by a different user and exactly one ERP change request). unit 212, integration 93 passed; combined coverage 91% (>=80%)
## Eval impact (baseline run id → new run id, deltas) or "n/a"
n/a
## Risks / follow-ups
none known
## Self-review checklist
- [x] tests added/updated   - [x] types pass   - [x] lint passes
- [x] no secrets            - [x] logs added for new code paths
- [x] docs updated          - [x] error handling covers failure modes
