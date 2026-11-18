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
