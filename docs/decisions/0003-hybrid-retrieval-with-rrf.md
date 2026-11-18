# 0003 - Hybrid retrieval with Reciprocal Rank Fusion

## Context
Datasheet questions contain exact identifiers (part numbers) and paraphrased concepts. Vector
search is good at the latter, keyword search at the former.

## Options considered
`vector` only, `keyword` only, `hybrid` (RRF, k=60, top 30 of each), `hybrid` + cross-encoder rerank.

## Decision
`RETRIEVAL_MODE=hybrid` is the default, with `vector`, `keyword` and optional rerank selectable per
call. Evidence (docs/EXPERIMENTS.md, dev n=56 / test n=37): keyword-only is clearly worse;
**hybrid is not distinguishable from vector-only** (recall@5 0.911 vs 0.875 on dev, within noise)
and vector-only is numerically equal or better at the top ranks on both splits. Hybrid is kept as a
judgement call (robustness to exact identifiers on real datasheets that this synthetic corpus may
not stress), explicitly *not* as a measured win. Rerank improved top-rank quality (dev recall@1 0.875
vs 0.554) but costs ~800 ms on CPU, so it is off by default.

## Consequences
- The default can be flipped with one environment variable if real-data evaluation prefers `vector`.
- A reranker must see the same text as the embedder (context header + content); an early version that
  scored bare content made retrieval worse (recall@5 0.589) - kept in the experiment record.
