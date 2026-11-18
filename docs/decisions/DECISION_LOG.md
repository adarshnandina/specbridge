# Decision log (small decisions; larger ones are ADRs)

| date | decision | reason |
|---|---|---|
| 2026-11-18 | Flat layout `specbridge/` at repo root, Python pinned `>=3.12,<3.13` | Spec Section 4; the pre-initialised `src/` layout was replaced |
| 2026-11-18 | `chunks.search_text` column added; `content_tsv` generated from it | Context header must be FTS-indexed while `content` stays clean for citations |
| 2026-11-18 | Pricing from platform.claude.com pricing page (verified 2026-11-18); model IDs from the build environment | Pricing page lists names/prices, not API IDs; re-check IDs before the first paid run |
| 2026-11-18 | 9 real datasheets instead of 10-20 | Several vendor sites block automated downloads; multi-model catalogs unsuitable for single-component labels |
| 2026-11-18 | Fake provider cost = 0, unknown priced models raise | Never report a silent zero cost for a real model |
| 2026-11-18 | Keyword search: OR of content words via `websearch_to_tsquery` | AND semantics match nothing for natural-language questions |
| 2026-11-18 | Abstention signal = best vector similarity regardless of retrieval mode | RRF scores are rank-based and not calibratable |
| 2026-11-18 | Approving a `pending_review` extraction requires a human review mark; no four-eyes for extractions | Spec requires four-eyes only for agent change requests |
| 2026-11-18 | Agent proposal needs >=1 verified claim, else ESCALATED | Never recommend on unverified rationale |
| 2026-11-18 | Agent scenarios seed approved extractions from ground truth | They test the agent, not the extractor |
| 2026-11-18 | ERP fault injection applies to writes only; added `lose_response_first_n` | Lookups must work when writes are down; lost responses are the case idempotency exists for |
| 2026-11-18 | Gate adds `ops_noise_floor` (20 ms) | A 25% p95 rule is below machine noise for a ~25 ms stage |
| 2026-11-18 | Gate compares only datasets a suite depends on | Unrelated dataset edits should not invalidate a retrieval baseline |
| 2026-11-18 | Baseline = full **dev** run (fake provider for LLM suites); test-split report kept separately | CI gate runs on dev so developers never iterate against test |
| 2026-11-18 | Final defaults unchanged after experiments (layout+header, hybrid, rerank off, ABSTAIN_MIN_SCORE=0.0) | See docs/EXPERIMENTS.md |
| 2026-11-18 | Reranker scores context header + content | Experiment 3 showed bare content makes reranking harmful |
