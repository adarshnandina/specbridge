# 6.1 Rate limiting, upload hardening, redaction tests, pip-audit
## Summary
Per-API-key moving-window rate limit middleware (limits library; /health /ready /metrics exempt; error format with request id); upload hardening: magic bytes, size limit with bounded read, filename sanitisation, page-count cap (400); redaction tests (log values, headers, LLM payload log, provider error text, request logs never contain X-API-Key/Authorization); pip-audit run
## Why
Part of milestone task 6.1 in SPECBRIDGE_SPEC.md Section 13.
## Changes (files/modules)
specbridge/api/middleware.py specbridge/api/main.py specbridge/ingestion/pipeline.py pyproject.toml uv.lock tests/unit/test_security.py tests/integration/test_api_docs_query.py
## How it was tested (commands + results)
unit test_security 7 passed; integration upload hardening test; full suite 303 passed
## Eval impact (baseline run id → new run id, deltas) or "n/a"
n/a
## Risks / follow-ups
none known
## Self-review checklist
- [x] tests added/updated   - [x] types pass   - [x] lint passes
- [x] no secrets            - [x] logs added for new code paths
- [x] docs updated          - [x] error handling covers failure modes
