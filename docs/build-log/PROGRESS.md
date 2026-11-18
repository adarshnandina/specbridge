# SpecBridge build progress

## Needs user
- Restart Claude Code (and approve the hooks in `/hooks` if prompted) so tool-call logging becomes active.
- (Docker blocker from 2026-11-18 resolved: daemon running.)
- Model IDs (`claude-haiku-5-5`, `claude-sonnet-5-5`) come from the build environment; the pricing page lists names and prices only. Prices verified 2026-11-18 (see `config/pricing.yaml`). Please re-check model IDs on the models overview page before the first paid run.

## Tasks
Status: todo | in progress | done | blocked

### M0 — Foundations
- 0.1 Prereqs, git, .gitignore, CLAUDE.md, build-log — done (2026-11-18, c04b9e8)
- 0.2 Hook logger + settings + tests — done (2026-11-18, 7dcf02f)
- 0.3 pyproject/uv/ruff/mypy/pytest/pre-commit/Makefile — done (2026-11-18, 6391ee0)
- 0.4 config, logging, middleware, /health /ready /metrics — done (2026-11-18, 09b929c)
- 0.5 docker-compose db + Alembic + initial migration — todo
- 0.6 LLM provider layer — todo
- 0.7 Auth + RBAC + audit — todo
### M1 — Corpus and datasets
- 1.1 Synthetic datasheet generator + ground truth — todo
- 1.2 Real datasheet manifest + fetch + provisional labels — todo
- 1.3 qa.jsonl + dataset validation — todo
- 1.4 ERP mock + seed + faults + tests — todo
### M2 — Ingestion, retrieval, Q&A, eval core
- 2.1 Parser, chunking, embeddings, ingestion pipeline, CLI — todo
- 2.2 Retrieval — todo
- 2.3 Q&A service — todo
- 2.4 API routes documents/query + page images — todo
- 2.5 UI login/ask/documents — todo
- 2.6 Eval core + retrieval/QA suites — todo
- 2.7 First retrieval baseline + QA fake run — todo
### M3 — Extraction
- 3.1 Schema, extractor, units, validators, retry — todo
- 3.2 Review queue, approve/reject, push — todo
- 3.3 API routes + UI review — todo
- 3.4 Extraction eval suite — todo
### M4 — Agent
- 4.1 State machine, tools, allowlists, limits — todo
- 4.2 Approval flow, four-eyes, retries, resume — todo
- 4.3 API routes + UI approvals/timeline — todo
- 4.4 Agent scenario suite (14) — todo
### M5 — Experiments and gating
- 5.1 eval gate + thresholds — todo
- 5.2 Experiments — todo
- 5.3 Final defaults + baseline — todo
### M6 — Hardening and docs
- 6.1 Rate limiting, upload hardening, redaction tests, pip-audit — todo
- 6.2 Dockerfile, compose, prod compose, e2e — todo
- 6.3 CI workflow — todo
- 6.4 Documentation + ADRs — todo
- 6.5 Final verification — todo
