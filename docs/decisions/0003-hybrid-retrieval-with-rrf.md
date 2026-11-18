# 0003 - Retrieval modes: vector default, hybrid (RRF) and rerank available

## Context
Datasheet questions contain exact identifiers (part numbers) and paraphrased concepts. Vector
search is good at the latter, keyword search at the former.

## Options considered
`vector` only, `keyword` only, `hybrid` (RRF, k=60, top 30 of each), `hybrid` + cross-encoder rerank.

## Decision
**Revised after re-measurement.** I first made `hybrid` the default (rationale: exact part-number
robustness), but the experiments, re-run after fixing a tie-ordering reproducibility bug (see
docs/EXPERIMENTS.md), showed hybrid scoring below vector-only on every metric on both splits (dev
recall@5 0.768 vs 0.875, recall@1 0.518 vs 0.607; test 0.865 vs 0.892 and 0.622 vs 0.757; the recall@5
intervals overlap). By the pre-set protocol (within noise -> prefer the simpler option), **the default is
`RETRIEVAL_MODE=vector`**. `keyword` and `hybrid` (RRF, k=60, top 30 of each, tie-aware ranks) remain
selectable per call, and the optional cross-encoder rerank (dev recall@1 0.893 vs 0.607, ~800 ms on CPU)
is off by default.

## Consequences
- The default can be flipped with one environment variable if real-data evaluation prefers `hybrid` (real part numbers may behave differently from the synthetic ones).
- A reranker must see the same text as the embedder (context header + content); an early version that
  scored bare content made retrieval worse (recall@5 0.589) - kept in the experiment record.
