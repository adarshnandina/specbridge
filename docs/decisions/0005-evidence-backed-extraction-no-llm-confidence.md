# 0005 - Evidence-backed extraction with deterministic validation (no LLM confidence)

## Context
Extracted specs are pushed to an ERP. LLM self-reported confidence is poorly calibrated and cannot
be audited.

## Decision
Every extracted field carries `{value, unit, page, quote}`. A deterministic pipeline normalises units
(pint, decimal commas, en-dash/ellipsis ranges, IP forms, alias maps) and validates: required
fields, `min <= max`, physical plausibility, IP regex, the quote fuzzy-matching the cited page
(>= 85) and the value's numbers being present in the quote (with unit scaling). Failure triggers one
retry with the errors appended; otherwise `pending_review`. Humans can edit (audited with old/new
values; validation re-runs on save); an approver approves; the push uses
`sha256(extraction_id + schema_version)` as idempotency key. There is no confidence field in the
schema and nothing in the pipeline reads one.

## Consequences
- A quote differing from the page by one digit still fuzzy-matches, which is why the separate
  numbers-in-quote check exists; semantic mistakes with a valid quote can still pass (the fake
  extractor read "301" from "AL-PSU-301" as a power value). The suite therefore reports the
  **precision of validated records**, the metric that says whether validation can be trusted.
- Real-model numbers for this metric are not yet measured (blocked: needs API key).
