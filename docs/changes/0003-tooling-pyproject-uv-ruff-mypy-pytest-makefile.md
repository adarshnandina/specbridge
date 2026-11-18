# 0.3 Tooling: pyproject, uv, ruff, mypy, pytest, Makefile
## Summary
uv project with flat specbridge/ layout, ruff, strict mypy, pytest, pre-commit config, Makefile targets, .env.example
## Why
Part of milestone task 0.3 in SPECBRIDGE_SPEC.md Section 13.
## Changes (files/modules)
pyproject.toml Makefile .pre-commit-config.yaml .env.example .dockerignore
## How it was tested (commands + results)
uv sync ok; ruff/mypy clean
## Eval impact (baseline run id → new run id, deltas) or "n/a"
n/a
## Risks / follow-ups
none known
## Self-review checklist
- [x] tests added/updated   - [x] types pass   - [x] lint passes
- [x] no secrets            - [x] logs added for new code paths
- [x] docs updated          - [x] error handling covers failure modes
