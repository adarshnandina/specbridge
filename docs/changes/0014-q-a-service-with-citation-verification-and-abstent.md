# 2.3 Q&A service with citation verification and abstention
## Summary
Versioned prompt qa_answer.v1 (sources untrusted, verbatim quotes), sources wrapped in <source> tags with closing-tag escaping, forced submit_answer tool, rapidfuzz citation verification (partial_ratio>=90 after dash/ellipsis/pipe normalisation), dropped invalid citations, unsupported-answer blocking, retrieval-score abstention without an LLM call, query_logs row; deterministic extractive fake responder for pipeline checks
## Why
Part of milestone task 2.3 in SPECBRIDGE_SPEC.md Section 13.
## Changes (files/modules)
specbridge/qa/* specbridge/prompts/qa_answer.v1.md specbridge/llm/fake_handlers.py tests/unit/test_citations.py tests/integration/test_qa.py
## How it was tested (commands + results)
unit test_citations 6 passed; integration test_qa 7 passed (valid citation + query log, invalid dropped, unsupported blocked, model-unanswerable, low-score abstain w/o LLM call, injection text only inside source tags, fake end-to-end). Whole suite 93 passed
## Eval impact (baseline run id → new run id, deltas) or "n/a"
n/a
## Risks / follow-ups
none known
## Self-review checklist
- [x] tests added/updated   - [x] types pass   - [x] lint passes
- [x] no secrets            - [x] logs added for new code paths
- [x] docs updated          - [x] error handling covers failure modes
