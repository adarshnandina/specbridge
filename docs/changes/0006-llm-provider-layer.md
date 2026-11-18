# 0.6 LLM provider layer
## Summary
LLMProvider protocol; Fake/Anthropic/Bedrock providers; tenacity retries; pricing.yaml (prices verified from platform.claude.com 2026-11-18); budget guard; SQLite response cache; usage accounting; forced-tool structured output with one retry
## Why
Part of milestone task 0.6 in SPECBRIDGE_SPEC.md Section 13.
## Changes (files/modules)
specbridge/llm/* specbridge/prompts/__init__.py config/pricing.yaml
## How it was tested (commands + results)
tests/unit/test_llm.py 10 passed; integration llm_calls row + db budget
## Eval impact (baseline run id → new run id, deltas) or "n/a"
n/a
## Risks / follow-ups
none known
## Self-review checklist
- [x] tests added/updated   - [x] types pass   - [x] lint passes
- [x] no secrets            - [x] logs added for new code paths
- [x] docs updated          - [x] error handling covers failure modes
