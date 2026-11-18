# 3.1 Extraction schema, extractor, normalisation, validators, retry loop
## Summary
ComponentSpec schema (FieldValue with page+quote, no confidence field); pint-based unit normalisation (decimal commas, en-dash and ellipsis ranges, mA/kW/kg, IP forms, interface/cert alias maps); deterministic validators (required, min<=max, plausibility, IP regex, evidence quote on cited page >=85, numbers supported by quote, category warnings); extractor with page selection, untrusted-data page tags, one retry with errors, status validated|pending_review; rule-based fake extractor
## Why
Part of milestone task 3.1 in SPECBRIDGE_SPEC.md Section 13.
## Changes (files/modules)
specbridge/extraction/* specbridge/prompts/extraction.v1.md specbridge/llm/usage.py tests/unit/test_units.py tests/unit/test_extraction.py
## How it was tested (commands + results)
unit: test_units 56, test_extraction 13 (normalisation, every validator rule, retry loop success/failure, page selection, escaping). Whole unit suite green
## Eval impact (baseline run id → new run id, deltas) or "n/a"
n/a
## Risks / follow-ups
none known
## Self-review checklist
- [x] tests added/updated   - [x] types pass   - [x] lint passes
- [x] no secrets            - [x] logs added for new code paths
- [x] docs updated          - [x] error handling covers failure modes
