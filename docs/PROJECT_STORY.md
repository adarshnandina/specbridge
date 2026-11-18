# SpecBridge - project story

*One page for applications. Every number comes from a run in `eval_results/` (ids given); anything
not yet measured is marked as such.*

## The problem

Engineers selecting or replacing industrial components lose hours in PDF datasheets: values hide in
tables with different units and formats, revisions silently change specs, and when a part is
discontinued someone has to find a compatible replacement and update the ERP. A chatbot that merely
sounds right is dangerous here: a wrong supply voltage damages hardware, and a system that can write
to an ERP must not be talked into it by text inside a PDF.

## What I built

SpecBridge ingests datasheets and offers three things on one evidence-first core:

1. **Cited Q&A.** Hybrid retrieval over layout-aware chunks; every answer claim needs a quote that is
   verified against the source chunk; the UI opens the datasheet page with the cited region highlighted; it
   abstains rather than guess.
2. **Auditable extraction.** Each spec field carries its page and quote; units and formats are normalised
   and validated by deterministic code (no LLM confidence anywhere); a review queue with audited edits; approved records reach
   the ERP exactly once through idempotency keys.
3. **A part-substitution agent with a human gate.** An explicit state machine that searches compatible,
   non-discontinued candidates with parameterised SQL, ranks them with cited evidence, and cannot write
   to the ERP without an approval from a *different* user - enforced by per-state tool allowlists and a write
   guard in code, not by prompts. It is resumable after a crash.

Around it: an evaluation framework (retrieval, QA, extraction, agent, ops) with dev/test splits, Wilson
intervals, a regression gate, and a record of every experiment; structured logs, per-call LLM cost
records, an audit log, RBAC, Docker, and 300+ tests (91% coverage).

## How it was evaluated

A deterministic synthetic corpus (51 datasheets, 4 layouts, format traps, revisions, discontinued parts, a
prompt-injection datasheet) gives exact ground truth for 108 generated questions and the extraction labels;
9 real public datasheets act as distractors and a small provisional test. Retrieval is measured on dev (n=56) and
confirmed once on test (n=37). The agent is tested through the real HTTP API with 15 scenarios, including a
scripted *compromised model* that obeys injected instructions.

## What testing changed (real results, with run ids)

- **Context headers were the biggest lever.** Prefixing chunks with `[vendor | part | title | rev | section]`
  raised recall@5 from 0.43 to 0.91 on dev (`20261118-134705_ba6fde4_exp4-header-off` vs
  `20261118-134704_ba6fde4_exp4-header-on`) and 0.43 to 0.87 on test.
- **I had misattributed a gain.** Layout chunking beat fixed chunking (0.91 vs 0.64), but the header was only
  on one side. A control with headers on both sides showed no significant difference
  (`20261118-135103_ba6fde4_exp1-chunking-fixed-header`), so I stopped claiming layout-aware chunking helps retrieval.
- **A reranker made retrieval worse until I fixed it.** It scored chunks without their header (recall@5 0.59,
  `20261118-134620_ba6fde4_exp3-hybrid-rerank` before the fix); scoring header + content gives recall@1 0.875 vs
  0.554 (`20261118-134750_ba6fde4_exp3-hybrid-rerank`), at ~800 ms per query, so it stays opt-in.
- **Hybrid search did not beat vector-only** here (within noise), and **no retrieval-score abstention threshold
  generalised from dev to test**, so abstention relies on citation verification and the model's own flag.
- **A safety test exposed a blind spot in my own harness.** Replacing the stable idempotency key with a random one
  went undetected until I added an ERP fault where the write succeeds but the response is lost (scenario S15).
- **A "configured" rate limiter did nothing** (slowapi silently exempted every route with the installed FastAPI);
  the test I wrote for it caught that, and I replaced it.
- **The gate catches regressions:** a deliberately degraded retrieval run fails it with exit code 1
  (`20261118-134429_9ae7ca4_deliberate-regression`, recall@5 0.911 -> 0.536).
- **Agent safety:** 15/15 scenarios and 6/6 safety scenarios pass (`20261118-135200_e64a52b_baseline-dev-all`).
  Mutation checks - removing the allowlist entry, the four-eyes check, the discontinued filter or the stable
  key - each make a scenario fail.

## Limitations (the short, honest version)

- **No real-LLM results yet.** No API key was available, so QA accuracy, abstention, citation quality, extraction F1 and
  the judge were only exercised with a fake provider (pipeline checks, labelled as such). One dev QA run is
  estimated at ~$0.035; extraction-model and retry-loop experiments have ready configs.
- Synthetic data is cleaner than reality and the evaluation sets are small (wide intervals); real-datasheet labels are
  drafts marked unverified; the judge is uncalibrated; no OCR; keyword search is Postgres FTS, not BM25; single node,
  mock ERP, static API keys. Nothing has been deployed.
- Placeholder: *real-model QA accuracy and extraction F1 - to be filled in after running
  `make eval-all` with a key (`docs/EVALUATION.md`).*

## What I would do next

Run the real-model evaluations and the two blocked experiments, have a domain engineer verify the real labels and score the
judge set, swap the mock ERP for the client's contract, add OCR and table-structure recognition, and build a larger
evaluation set from the client's own datasheets.
