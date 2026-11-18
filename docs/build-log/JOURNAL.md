# SpecBridge build journal (append-only)

## 2026-11-18 — 0.1 Prerequisites, git, CLAUDE.md, build log
**Goal:** Check prerequisites and lay down project rules and logs.
**What I did:**
- Checked tools: Python 3.12 available via uv (system python is 3.14.7, project pins 3.12), uv 0.13.5, make 3.81, git 2.56, Docker CLI 29.8.1 + Compose v5.5.1.
- Docker daemon NOT running (socket missing) -> prerequisite blocker per Section 0.4.
- Existing local git repo (no commits, no remote), `.python-version`=3.12, stub `src/specbridge`.
- Wrote .gitignore, CLAUDE.md, PROGRESS.md, JOURNAL.md.
**Files changed:** .gitignore, CLAUDE.md, docs/build-log/*
**Commands run and outcome:** `docker ps` fail (daemon down); others pass.
**Tests:** n/a
**Problems:** Docker not running; asking user to start it.
**Decisions made:** none yet
**Deviations from spec:** none
**Next step:** user starts Docker, then continue with 0.2.

## 2026-11-18 13:00 — 0.2 Hook logger and settings
**Goal:** Claude Code hook script logging redacted tool calls to logs/dev, plus .claude/settings.json
**What I did:** Claude Code hook script logging redacted tool calls to logs/dev, plus .claude/settings.json
**Files changed:** scripts/dev/log_tool_call.py .claude/settings.json tests/unit/test_hook_logger.py
**Commands run and outcome:** make lint typecheck test (pass)
**Tests:** 3 passed (tests/unit/test_hook_logger.py: truncation, redaction, always exit 0)
**Eval results (if any):** n/a
**Problems and how I solved them:** none
**Decisions made:** none
**Deviations from spec:** none
**Next step:** next task in PROGRESS.md

## 2026-11-18 13:01 — 0.3 Tooling: pyproject, uv, ruff, mypy, pytest, Makefile
**Goal:** uv project with flat specbridge/ layout, ruff, strict mypy, pytest, pre-commit config, Makefile targets, .env.example
**What I did:** uv project with flat specbridge/ layout, ruff, strict mypy, pytest, pre-commit config, Makefile targets, .env.example
**Files changed:** pyproject.toml Makefile .pre-commit-config.yaml .env.example .dockerignore
**Commands run and outcome:** make lint typecheck test (pass)
**Tests:** uv sync ok; ruff/mypy clean
**Eval results (if any):** n/a
**Problems and how I solved them:** Code committed together with 0.2 in commit 59692d6 (batched staging); this commit records the task.
**Decisions made:** Flat layout specbridge/ at repo root instead of pre-initialised src/ layout (matches spec Section 4); uv_build module-root=''. Python pinned >=3.12,<3.13.
**Deviations from spec:** Python upper bound pinned <3.13 for dependency compatibility
**Next step:** next task in PROGRESS.md

## 2026-11-18 13:01 — 0.4 Config, logging, middleware, health endpoints
**Goal:** pydantic-settings config with fail-fast validation, structlog JSON logging with redaction, request-id middleware, error format, rate limiting, /health /ready /metrics
**What I did:** pydantic-settings config with fail-fast validation, structlog JSON logging with redaction, request-id middleware, error format, rate limiting, /health /ready /metrics
**Files changed:** specbridge/config.py logging_setup.py metrics.py errors.py api/*
**Commands run and outcome:** make lint typecheck test (pass)
**Tests:** tests/unit/test_config.py, test_logging.py, test_api_basic.py pass
**Eval results (if any):** n/a
**Problems and how I solved them:** Code committed together with 0.2 in commit 59692d6 (batched staging); this commit records the task.
**Decisions made:** none
**Deviations from spec:** none
**Next step:** next task in PROGRESS.md

## 2026-11-18 13:01 — 0.5 Postgres+pgvector, Alembic, initial migration
**Goal:** SQLAlchemy models for all Section 6 tables, docker-compose db service, Alembic env, migration 0001 with vector extension, HNSW and GIN indexes, generated tsvector
**What I did:** SQLAlchemy models for all Section 6 tables, docker-compose db service, Alembic env, migration 0001 with vector extension, HNSW and GIN indexes, generated tsvector
**Files changed:** specbridge/db/* alembic/* docker-compose.yml
**Commands run and outcome:** make lint typecheck test (pass)
**Tests:** integration test_migrations_up_down_up passes against testcontainers pgvector
**Eval results (if any):** n/a
**Problems and how I solved them:** Code committed together with 0.2 in commit 59692d6 (batched staging); this commit records the task.
**Decisions made:** chunks has extra search_text column so the context header is FTS-indexed while content stays clean for citations
**Deviations from spec:** added chunks.search_text column (spec: content_tsv generated from content; header must be indexed per 7.3)
**Next step:** next task in PROGRESS.md

## 2026-11-18 13:01 — 0.6 LLM provider layer
**Goal:** LLMProvider protocol; Fake/Anthropic/Bedrock providers; tenacity retries; pricing.yaml (prices verified from platform.claude.com 2026-11-18); budget guard; SQLite response cache; usage accounting; forced-tool structured output with one retry
**What I did:** LLMProvider protocol; Fake/Anthropic/Bedrock providers; tenacity retries; pricing.yaml (prices verified from platform.claude.com 2026-11-18); budget guard; SQLite response cache; usage accounting; forced-tool structured output with one retry
**Files changed:** specbridge/llm/* specbridge/prompts/__init__.py config/pricing.yaml
**Commands run and outcome:** make lint typecheck test (pass)
**Tests:** tests/unit/test_llm.py 10 passed; integration llm_calls row + db budget
**Eval results (if any):** n/a
**Problems and how I solved them:** Code committed together with 0.2 in commit 59692d6 (batched staging); this commit records the task. Test bug: 1M tokens exceeded Haiku long-context threshold; fixed the test not the code.
**Decisions made:** LLMService wraps providers; fake provider costs 0; unknown priced model raises
**Deviations from spec:** none
**Next step:** next task in PROGRESS.md

## 2026-11-18 13:01 — 0.7 Auth, RBAC, audit
**Goal:** API key store with constant-time compare, permission matrix, FastAPI require() dependency, append-only audit log, denials audited in separate transaction
**What I did:** API key store with constant-time compare, permission matrix, FastAPI require() dependency, append-only audit log, denials audited in separate transaction
**Files changed:** specbridge/auth/* audit.py api/deps.py
**Commands run and outcome:** make lint typecheck test (pass)
**Tests:** tests/unit/test_auth.py pass; integration test_audit_and_denied_survive
**Eval results (if any):** n/a
**Problems and how I solved them:** Code committed together with 0.2 in commit 59692d6 (batched staging); this commit records the task. Denial audit uses its own session so the request rollback cannot drop it.
**Decisions made:** none
**Deviations from spec:** none
**Next step:** M1.1 synthetic datasheet generator

## 2026-11-18 13:05 — 1.1 Synthetic datasheet generator and ground truth
**Goal:** Deterministic generator (seed 42): 3 fictional vendors, 45 parts + 5 rev1.1 + 1 prompt-injection datasheet = 51 PDFs in 4 layout families with format variety; ground truth with per-field evidence pages, lifecycle, replacement candidates; shared candidate rule in specbridge/extraction/fields.py
**What I did:** Deterministic generator (seed 42): 3 fictional vendors, 45 parts + 5 rev1.1 + 1 prompt-injection datasheet = 51 PDFs in 4 layout families with format variety; ground truth with per-field evidence pages, lifecycle, replacement candidates; shared candidate rule in specbridge/extraction/fields.py
**Files changed:** corpus/synthetic/* specbridge/extraction/fields.py eval/datasets/extraction_synthetic.jsonl tests/unit/test_corpus.py
**Commands run and outcome:** make lint typecheck test (pass)
**Tests:** tests/unit/test_corpus.py 8 passed (counts, determinism, revisions, scenario invariants, injection doc)
**Eval results (if any):** n/a
**Problems and how I solved them:** Initial hash-based split gave 23/28; replaced with rank-based split. Ruff E501 disabled (formatter wraps; long data strings).
**Decisions made:** Hand-crafted override parts (orphans KD-310/NS-PRS-3400, constraint-scenario NS-IND-1200..1208, injection scenario AL-DIO-101/103/199) guarantee agent scenarios are well-defined; 60/40 dev/test split by sorted part number; GT also stores replacement_candidates
**Deviations from spec:** none
**Next step:** next task in PROGRESS.md
