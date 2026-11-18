# 2.4 API routes: documents, query, highlighted page images
## Summary
POST/GET /documents (magic-byte + size checks, bounded read, audit), POST /query (Pydantic validated, whitelisted modes), GET page image PNG with cited bboxes highlighted and cached under data/cache/pages; shared integration fixtures (TestClient with fake LLM, isolated DATA_DIR)
## Why
Part of milestone task 2.4 in SPECBRIDGE_SPEC.md Section 13.
## Changes (files/modules)
specbridge/api/routers/{documents,query}.py specbridge/api/main.py tests/integration/conftest.py tests/integration/test_api_docs_query.py
## How it was tested (commands + results)
integration test_api_docs_query 8 passed (401/403 + audited denial, upload/list/get/idempotent, non-PDF and oversize rejected, query + highlighted image differs from plain + cache hit, validation, abstain on empty corpus)
## Eval impact (baseline run id → new run id, deltas) or "n/a"
n/a
## Risks / follow-ups
none known
## Self-review checklist
- [x] tests added/updated   - [x] types pass   - [x] lint passes
- [x] no secrets            - [x] logs added for new code paths
- [x] docs updated          - [x] error handling covers failure modes
