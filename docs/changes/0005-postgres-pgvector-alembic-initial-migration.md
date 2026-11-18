# 0.5 Postgres+pgvector, Alembic, initial migration
## Summary
SQLAlchemy models for all Section 6 tables, docker-compose db service, Alembic env, migration 0001 with vector extension, HNSW and GIN indexes, generated tsvector
## Why
Part of milestone task 0.5 in SPECBRIDGE_SPEC.md Section 13.
## Changes (files/modules)
specbridge/db/* alembic/* docker-compose.yml
## How it was tested (commands + results)
integration test_migrations_up_down_up passes against testcontainers pgvector
## Eval impact (baseline run id → new run id, deltas) or "n/a"
n/a
## Risks / follow-ups
none known
## Self-review checklist
- [x] tests added/updated   - [x] types pass   - [x] lint passes
- [x] no secrets            - [x] logs added for new code paths
- [x] docs updated          - [x] error handling covers failure modes
