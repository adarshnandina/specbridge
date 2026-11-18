# 1.2 Real datasheet manifest, fetch script, provisional labels
## Summary
9 real public datasheets (ifm, Omron, Lantronix, Wachendorff, wenglor, Bernstein) located via web search, verified as PDFs, listed in corpus/real/manifest.yaml with sha256; fetch.py re-downloads and verifies; draft labels in eval/datasets/extraction_real.jsonl all verified_by_human=false
## Why
Part of milestone task 1.2 in SPECBRIDGE_SPEC.md Section 13.
## Changes (files/modules)
corpus/real/* eval/datasets/extraction_real.jsonl
## How it was tested (commands + results)
fetch.py run: 9 verified, 0 problems (network, manual run; not part of the test suite)
## Eval impact (baseline run id → new run id, deltas) or "n/a"
n/a
## Risks / follow-ups
none known
## Self-review checklist
- [x] tests added/updated   - [x] types pass   - [x] lint passes
- [x] no secrets            - [x] logs added for new code paths
- [x] docs updated          - [x] error handling covers failure modes
