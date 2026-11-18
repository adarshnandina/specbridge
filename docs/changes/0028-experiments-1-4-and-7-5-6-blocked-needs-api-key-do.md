# 5.2 Experiments 1-4 and 7 (5-6 blocked: needs API key); docs/EXPERIMENTS.md
## Summary
Retrieval-side experiments run on dev and confirmed once on test: chunking (+ a fixed+header control), retrieval mode, reranker (found and fixed a real bug: reranker must see the context header), context header, abstention-threshold calibration (new calibration suite). Tables in docs/EXPERIMENTS.md are generated from run files
## Why
Part of milestone task 5.2 in SPECBRIDGE_SPEC.md Section 13.
## Changes (files/modules)
specbridge/eval/{calibration,experiments}.py experiments/*.yaml docs/EXPERIMENTS.md eval_results/*exp* specbridge/retrieval/service.py specbridge/ingestion/chunking.py specbridge/cli.py
## How it was tested (commands + results)
unit test_calibration 2; integration test_retrieval (reranker input includes context header) ; test_chunking (fixed+header)
## Eval impact (baseline run id → new run id, deltas) or "n/a"
See docs/EXPERIMENTS.md (all run ids). Key results (dev, n=56): header on/off recall@5 0.911 vs 0.429; layout vs fixed 0.911 vs 0.643 but fixed+header 0.857 (within noise of layout); hybrid 0.911 vs vector 0.875 (within noise); rerank fixed: recall@1 0.875 vs 0.554 at ~800 ms; no abstention threshold generalises to test. Exp 5/6: blocked: needs API key
## Risks / follow-ups
none known
## Self-review checklist
- [x] tests added/updated   - [x] types pass   - [x] lint passes
- [x] no secrets            - [x] logs added for new code paths
- [x] docs updated          - [x] error handling covers failure modes
