# SpecBridge build progress

## Needs user
- **BLOCKER (2026-11-18): Docker daemon is not running** (`failed to connect to the docker API at unix:///Users/adarsh/.docker/run/docker.sock`). Please start Docker Desktop. Needed for the Postgres+pgvector integration tests, `docker compose`, and e2e tests.
- Restart Claude Code (and approve the hooks in `/hooks` if prompted) so tool-call logging becomes active.
- Note: repo was pre-initialised with `src/specbridge` layout (uv_build); spec Section 4 wants `specbridge/` at the root. Will be recorded as a decision.

## Tasks
Status: todo | in progress | done | blocked

### M0 — Foundations
- 0.1 Prereqs, git, .gitignore, CLAUDE.md, build-log — in progress
- 0.2 Hook logger + settings — todo
- 0.3 pyproject/uv/ruff/mypy/pytest/pre-commit/Makefile — todo
- 0.4 config, logging, middleware, /health /ready /metrics — todo
- 0.5 docker-compose db + Alembic + initial migration — todo (needs Docker)
- 0.6 LLM provider layer — todo
- 0.7 Auth + RBAC + audit — todo
### M1 — Corpus and datasets
- 1.1 Synthetic generator — todo
- 1.2 Real manifest/fetch — todo
- 1.3 qa.jsonl + validation — todo
- 1.4 ERP mock — todo
### M2 — Ingestion, retrieval, Q&A, eval core
- 2.1–2.7 — todo
### M3 — Extraction
- 3.1–3.4 — todo
### M4 — Agent
- 4.1–4.4 — todo
### M5 — Experiments and gating
- 5.1–5.3 — todo
### M6 — Hardening and docs
- 6.1–6.5 — todo
