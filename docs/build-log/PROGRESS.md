# SpecBridge build progress

## Needs user
- Restart Claude Code (and approve the hooks in `/hooks` if prompted) so tool-call logging becomes active.
- (Docker blocker from 2026-11-18 resolved: daemon running.)
- Model IDs (`claude-haiku-5-5`, `claude-sonnet-5-5`) come from the build environment; the pricing page lists names and prices only. Prices verified 2026-11-18 (see `config/pricing.yaml`). Please re-check model IDs on the models overview page before the first paid run.

- Verify real-datasheet labels in `eval/datasets/extraction_real.jsonl` (all `verified_by_human: false`; metrics on them are provisional). Only 9 of the 10-20 target real datasheets were obtainable (Baumer, ifm AL2301, Parker, Mean Well blocked automated downloads).
- **API key needed for paid runs** (`ANTHROPIC_API_KEY` in `.env`, or AWS credentials + `BEDROCK_MODEL_*` for Bedrock). Blocked until then: real QA eval (2.7), real extraction eval (3.4), live agent run (4.4), experiments 5-6 (5.2), real test-split final evaluation (5.3). Everything else runs on the fake provider. Estimated cost of one real dev QA run is printed by `specbridge eval run --dry-run --provider anthropic --suite qa`.

## Tasks
Status: todo | in progress | done | blocked

### M0 — Foundations
- 0.1 Prereqs, git, .gitignore, CLAUDE.md, build-log — done (2026-11-18, c04b9e8)
- 0.2 Hook logger + settings + tests — done (2026-11-18, 7dcf02f)
- 0.3 pyproject/uv/ruff/mypy/pytest/pre-commit/Makefile — done (2026-11-18, 6391ee0)
- 0.4 config, logging, middleware, /health /ready /metrics — done (2026-11-18, 09b929c)
- 0.5 docker-compose db + Alembic + initial migration — done (2026-11-18, f7c6e05)
- 0.6 LLM provider layer — done (2026-11-18, 0d925bf)
- 0.7 Auth + RBAC + audit — done (2026-11-18, 05d9f56)
### M1 — Corpus and datasets
- 1.1 Synthetic datasheet generator + ground truth — done (2026-11-18, dba5846)
- 1.2 Real datasheet manifest + fetch + provisional labels — done (2026-11-18, 4964190)
- 1.3 qa.jsonl + dataset validation — done (2026-11-18, 7bd9d9c)
- 1.4 ERP mock + seed + faults + tests — done (2026-11-18, 99d4466)
### M2 — Ingestion, retrieval, Q&A, eval core
- 2.1 Parser, chunking, embeddings, ingestion pipeline, CLI — done (2026-11-18, b88aa3b)
- 2.2 Retrieval — done (2026-11-18, 44314e7)
- 2.3 Q&A service — done (2026-11-18, 0caf647)
- 2.4 API routes documents/query + page images — done (2026-11-18, e3eae9a)
- 2.5 UI login/ask/documents — done (2026-11-18, cf88a3c)
- 2.6 Eval core + retrieval/QA suites — done (2026-11-18, 1bdf32d)
- 2.7 First retrieval baseline + QA fake run — done (2026-11-18, 95550ed)
### M3 — Extraction
- 3.1 Schema, extractor, units, validators, retry — done (2026-11-18, 4b9a0b0)
- 3.2 Review queue, approve/reject, push — done (2026-11-18, 113be86)
- 3.3 API routes + UI review — done (2026-11-18, bfe898b)
- 3.4 Extraction eval suite — done (2026-11-18, 8a5cf69)
### M4 — Agent
- 4.1 State machine, tools, allowlists, limits — done (2026-11-18, 276415a)
- 4.2 Approval flow, four-eyes, retries, resume — done (2026-11-18, eb9e745)
- 4.3 API routes + UI approvals/timeline — done (2026-11-18, d2125f1)
- 4.4 Agent scenario suite (14) — done (2026-11-18, 6af582b)
### M5 — Experiments and gating
- 5.1 eval gate + thresholds — done (2026-11-18, 693f6bb)
- 5.2 Experiments — done (2026-11-18, 2fe3763)
- 5.3 Final defaults + baseline — done (2026-11-18, c397129)
### M6 — Hardening and docs
- 6.1 Rate limiting, upload hardening, redaction tests, pip-audit — todo
- 6.2 Dockerfile, compose, prod compose, e2e — todo
- 6.3 CI workflow — todo
- 6.4 Documentation + ADRs — todo
- 6.5 Final verification — todo
