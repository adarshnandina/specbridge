# 0.4 Config, logging, middleware, health endpoints
## Summary
pydantic-settings config with fail-fast validation, structlog JSON logging with redaction, request-id middleware, error format, rate limiting, /health /ready /metrics
## Why
Part of milestone task 0.4 in SPECBRIDGE_SPEC.md Section 13.
## Changes (files/modules)
specbridge/config.py logging_setup.py metrics.py errors.py api/*
## How it was tested (commands + results)
tests/unit/test_config.py, test_logging.py, test_api_basic.py pass
## Eval impact (baseline run id → new run id, deltas) or "n/a"
n/a
## Risks / follow-ups
none known
## Self-review checklist
- [x] tests added/updated   - [x] types pass   - [x] lint passes
- [x] no secrets            - [x] logs added for new code paths
- [x] docs updated          - [x] error handling covers failure modes
