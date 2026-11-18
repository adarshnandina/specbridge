# Evaluation

How SpecBridge is measured, how the datasets were built, and what the current numbers are and are
not. Decisions and their rationale are in [ADR-0006](decisions/0006-evaluation-strategy-and-gating.md);
configuration experiments are in [EXPERIMENTS.md](EXPERIMENTS.md); caveats are in [LIMITATIONS.md](LIMITATIONS.md).

> **Read this first.** No API key was available during the build, so every number below that involves
> an LLM (QA accuracy, abstention, citations, extraction, judge) was produced by the **fake provider**:
> an extractive answer heuristic, a regex extractor and a constant judge. They verify that the
> pipelines, metrics and gates work. They say **nothing** about how a real model performs and are
> marked **(fake)**. The retrieval numbers and the agent safety scenarios are real measurements of the
> real code on the (synthetic) corpus.

## Datasets (`eval/datasets/`)

| file | content | how it was built |
|---|---|---|
| `extraction_synthetic.jsonl` | ground truth for 51 synthetic datasheets: normalised spec, evidence page per field, lifecycle, replacement candidates, split | emitted by the generator (`corpus/synthetic`, seed 42): correct by construction |
| `qa.jsonl` | 108 questions: factual 35, table_lookup 20, cross_doc 15, revision 8, unanswerable 15, injection 5, open 10 | `corpus/synthetic/qa_dataset.py`, computed from the ground truth; cross-doc answers are computed programmatically; unanswerable = 10 missing attributes + 3 non-existent parts + 2 null fields |
| `extraction_real.jsonl` | provisional labels for 9 real public datasheets | drafted by Claude from the PDF text; every record is `verified_by_human: false` |
| `agent_scenarios.yaml` | 15 scenarios (14 required + 1 extra) with setup, steps and expectations | hand-written; run through the real HTTP API |
| `judge_calibration.jsonl` | 20 candidate answers (10 questions x faithful/wrong) with an **empty** `human_score` | programmatic candidates, **not model output**; to be scored 1-3 by a human |
| `thresholds.yaml` | regression gate thresholds | spec Section 8.3 (+ a latency noise floor) |

**Splits.** Roughly 60/40 dev/test (QA: 65 dev / 43 test; extraction documents by sorted part number so
a part and its revision share a split). **Tuning uses dev; test is run once for confirmation.**
`specbridge eval validate-datasets` checks schema, minimum counts per type, split ratio, that every
expected `doc_key` exists, the judge set and that real labels are unverified.

## Metrics

- **Retrieval:** a *hit* is a retrieved chunk from an expected `doc_key` **and** an expected page.
  recall@k = share of questions with a hit within the top k; MRR = mean reciprocal rank of the first hit;
  reported per question type. Unanswerable items are excluded.
- **QA:** answer accuracy by match rule (`numeric` 1% tolerance with unit/decimal-comma handling,
  `set` incl. interface/certification aliases and extra-item penalty, `contains`, `exact` yes/no; `judge`
  for open items); abstention precision/recall on `expect_abstain` items; over-abstention on answerable
  items; injection resistance (no `forbidden` string in the answer); **citation precision** (valid citations
  whose chunk is an expected doc+page / all citations) and **citation coverage** (answered questions with
  at least one valid citation / answered); stale-revision rate; judge usefulness 1-3 (uncalibrated).
- **Extraction:** per-field and micro precision/recall/F1 (exact after normalisation, 1% numeric
  tolerance, `null` handled; a wrong value counts as both FP and FN), evidence validity rate, share
  auto-validated vs needing review, and **precision of validated records**.
- **Agent:** scenario pass rate and a separate pass rate for the safety scenarios (S05, S06, S07, S10,
  S11, S12), which must all pass; after every scenario global invariants are checked (ERP change
  requests == DONE runs; DONE only with an approved approval).
- **Ops:** p50/p95 latency per stage (cache hits excluded), tokens, cost per 100 queries and per extracted document.
- **Statistics:** n and 95% Wilson intervals for proportions; comparisons flag `significant` (disjoint
  CIs), `weak` (partial overlap) or `within noise` (>= 50% overlap of the narrower interval).
- **Reproducibility:** every run records the indexed corpus (documents/chunks), dataset hashes, config,
  model ids and prompt versions. Retrieval ordering is deterministic (ties broken by `doc_key`, `chunk_index`);
  two independent indexes of the same corpus give identical ranks.

## Running

```bash
make eval-retrieval                  # no LLM calls; writes eval_results/<run_id>.json + .md
make gate-retrieval                  # compare the latest 'ci' run with eval_results/baseline.json
uv run specbridge eval run --suite all --split dev --tag mytag --provider fake
uv run specbridge eval run --suite qa --split dev --provider anthropic --dry-run   # cost estimate only
uv run specbridge eval compare <run_a> <run_b>
uv run specbridge eval set-baseline <run>
uv run specbridge eval gate --candidate <run> --suite retrieval
```

Every run prints a **cost estimate first** and aborts if it exceeds `EVAL_MAX_COST_USD`; a run also
stops when its running cost passes the limit. `--use-cache` reuses cached LLM responses (hits are free
and excluded from latency). A paid run without an API key is refused.

## Gate

`specbridge eval gate` fails (exit 1) when the candidate is worse than the baseline by more than
`eval/thresholds.yaml` allows (recall@5 and MRR drop 0.03; QA accuracy and citation precision drop
0.03; abstention recall drop 0.05; extraction micro-F1 drop 0.02; p95 latency +25%; cost per 100
queries +20%; all agent safety scenarios must pass). It refuses to compare runs with different splits,
different datasets (only those a suite depends on) or different indexed corpora. Latency increases
below 20 ms absolute are ignored (noise floor). Proof that it works against the current baseline: the
keyword-only experiment run `20261118-142214_f14eb9c_exp2-mode-keyword` fails it with exit code 1
(recall@5 0.875 -> 0.464). An earlier proof run is `20261118-134429_9ae7ca4_deliberate-regression`.
The gate also earned its keep once: a clean checkout failed it and exposed the tie-ordering
reproducibility bug described in EXPERIMENTS.md.

## Judge calibration status

**Not calibrated.** `judge_calibration.jsonl` has no human scores yet. Until someone fills in
`human_score` (1-3), judge usefulness scores are *uncalibrated*, and with the fake provider the judge
returns a constant. Once scored, judge-human agreement should be computed and reported here.

## Final baseline and test-split report

- **Gate baseline** (`eval_results/baseline.json`): `20261118-142407_f14eb9c_baseline-dev-all` - full run on the **dev** split.
- **Final test-split report:** `20261118-142424_f14eb9c_final-test-all` - the same suites on the **test** split, run once.

Rows marked **(fake)** are pipeline checks, not model quality.

| metric | dev (`20261118-142407_f14eb9c_baseline-dev-all`) | test (`20261118-142424_f14eb9c_final-test-all`) |
|---|---|---|
| retrieval recall@1 | 0.607 [0.48, 0.72] (n=56) | 0.757 [0.60, 0.87] (n=37) |
| retrieval recall@3 | 0.821 [0.70, 0.90] (n=56) | 0.865 [0.72, 0.94] (n=37) |
| retrieval recall@5 | 0.875 [0.76, 0.94] (n=56) | 0.892 [0.75, 0.96] (n=37) |
| retrieval recall@10 | 0.964 [0.88, 0.99] (n=56) | 0.946 [0.82, 0.98] (n=37) |
| retrieval MRR | 0.722 (n=56) | 0.815 (n=37) |
| QA answer accuracy **(fake)** | 0.680 [0.54, 0.79] (n=50) | 0.545 [0.38, 0.70] (n=33) |
| QA abstention recall **(fake)** | 0.889 [0.56, 0.98] (n=9) | 1.000 [0.61, 1.00] (n=6) |
| QA abstention precision **(fake)** | 0.381 [0.21, 0.59] (n=21) | 0.316 [0.15, 0.54] (n=19) |
| QA injection resistance **(fake)** | 1.000 [0.44, 1.00] (n=3) | 1.000 [0.34, 1.00] (n=2) |
| QA citation precision **(fake)** | 0.909 [0.79, 0.96] (n=44) | 0.875 [0.69, 0.96] (n=24) |
| QA citation coverage **(fake)** | 1.000 [0.92, 1.00] (n=44) | 1.000 [0.86, 1.00] (n=24) |
| extraction micro-F1, synthetic **(fake)** | 0.992 (n=33 docs) | 0.993 (n=18 docs) |
| extraction: share auto-validated **(fake)** | 1.000 [0.90, 1.00] (n=33) | 1.000 [0.82, 1.00] (n=18) |
| extraction: precision of validated docs **(fake)** | 0.879 [0.73, 0.95] (n=33) | 0.889 [0.67, 0.97] (n=18) |
| extraction micro-F1, real labels **(fake, PROVISIONAL)** | 0.172 (n=6 docs) | 0.250 (n=3 docs) |
| agent scenarios passed | 1.000 [0.80, 1.00] (n=15) | 1.000 [0.80, 1.00] (n=15) |
| agent safety scenarios passed (6 must pass) | 1.000 [0.61, 1.00] (n=6) | 1.000 [0.61, 1.00] (n=6) |

Retrieval latency (dev baseline): p50 19 ms / p95 23 ms (vector, no rerank, 264 chunks, CPU).
Cost: $0.00 (fake provider).

**How to read these numbers.**
- Retrieval: real. recall@5 0.88 (dev) / 0.89 (test) with wide intervals; top-1 precision is lower
  (recall@1 0.61 on dev), which is what the reranker improves (EXPERIMENTS.md, experiment 3).
- QA, extraction (fake): the "answer" is the best-matching line of the best source, so accuracy is
  capped by retrieval and by the line heuristic (cross-document questions score 0 by construction);
  abstention precision is low because the heuristic abstains on many answerable questions. "Precision
  of validated docs" below 1.0 shows validation passing records that are wrong - the property that
  must be re-measured with a real model.
- Extraction on real datasheets scores low with the regex stand-in and against *provisional* labels;
  it demonstrates the pipeline on messy PDFs, nothing more.
- Agent: all scenarios and all safety scenarios pass with scripted model behaviour, including a
  model that obeys injected instructions.

## What a real evaluation would add

Run `make eval-all` with a key (estimated about $0.03-0.04 per dev QA run, printed by the runner),
score the judge calibration items, verify the real-datasheet labels, then
`specbridge eval set-baseline <run>` and re-run the gate. Experiments 5 and 6 have ready configs under `experiments/`.
