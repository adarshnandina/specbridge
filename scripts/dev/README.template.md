# SpecBridge

SpecBridge turns industrial component datasheets (PDFs) into a **question-answering assistant that cites the exact datasheet page and region it used**, a **validated, evidence-backed extraction pipeline** that pushes approved specs to an ERP, and a **part-substitution agent** that proposes replacements for discontinued parts but never writes anything without a second person's approval. An **evaluation framework** measures retrieval, answers, extraction and agent behaviour on every change and gates regressions against a baseline.

> **Status, honestly.** Built and tested end to end, with **no real LLM run yet** (no API key was available): QA, extraction and judge results below are *fake-provider pipeline checks*. Retrieval results and the agent safety scenarios are real measurements. Nothing has been deployed. See [LIMITATIONS](docs/LIMITATIONS.md).

```mermaid
flowchart LR
    U[Browser / curl] --> API[FastAPI + UI]
    API --> ING[Ingestion<br/>PyMuPDF, chunking, bge-small]
    API --> QA[Q&A<br/>vector retrieval, verified citations]
    API --> EX[Extraction<br/>units, validators, review]
    API --> AG[Agent<br/>explicit state machine]
    ING --> DB[(Postgres + pgvector)]
    QA --> DB
    EX --> DB
    AG --> DB
    QA --> LLM[LLM provider layer<br/>Anthropic / Bedrock / Fake]
    EX --> LLM
    AG --> LLM
    EX -->|idempotent PUT| ERP[ERP mock]
    AG -->|idempotent POST after approval| ERP
    EV[eval runner + gate] --> QA
    EV --> EX
    EV --> AG
```

## Features

- **Cited answers:** vector retrieval by default (keyword and hybrid RRF selectable; optional reranker); every claim needs a quote that is verified against the source chunk; the UI opens the datasheet page with the cited region highlighted; abstains when evidence is missing or unverifiable.
- **Extraction you can audit:** every field has `{{value, unit, page, quote}}`; deterministic unit normalisation (decimal commas, en-dash ranges, mA/kW, IP forms) and validation (plausibility, min<=max, quote on the cited page, numbers in the quote); human review queue with audited edits; idempotent push to the ERP. No LLM confidence is used.
- **Safe agent:** states `RECEIVED -> ... -> AWAITING_APPROVAL -> COMMITTING -> DONE`, per-state tool allowlists, write tool only after an approval by a *different* user, ERP calls with idempotency keys, resumable after a crash, 15 scenarios incl. a prompt-injection datasheet and a "compromised model".
- **Honest evaluation:** dev/test splits, Wilson intervals, "within noise" flags, deterministic retrieval, cost estimates before paid runs, a regression gate (`make gate-retrieval`), recorded experiments with run ids.
- **Operations:** structured JSON logs, per-call LLM cost/latency/prompt-version records, audit log, Prometheus metrics, RBAC with API keys, rate limiting, daily budget guard, Docker (non-root), Alembic migrations.

## Quickstart

Prerequisites: Python 3.12, [uv](https://docs.astral.sh/uv/), Docker with Compose v2, make.

```bash
cp .env.example .env            # LLM_PROVIDER=fake works without any API key
make setup                      # uv sync + pre-commit hooks
make up                         # docker compose: db, erp-mock, api (first build downloads the model, ~2.7 GB image)
make corpus                     # 51 synthetic PDFs + 9 real public datasheets into data/corpus (network for the real ones)
make ingest                     # chunk, embed and index them (host Python against the compose database)
open http://localhost:8000/ui/login   # paste dev-viewer-key, then /ui/ask
```

Ask "What is the protection class of the KD-210?" and click a source: you get the datasheet page with
the cited region highlighted. Log in with `dev-engineer-key` and `dev-approver-key` (in two browsers)
to try `/ui/review` and `/ui/runs`. Local checks: `make ci` (lint, types, unit + integration tests with
Testcontainers, coverage >= 80%, pip-audit, then db-up/migrate/ingest, retrieval eval and gate; needs Docker and network for the real datasheets),
`make test-e2e` against the running stack.

```bash
curl -s -X POST localhost:8000/query -H "X-API-Key: dev-viewer-key" -H "Content-Type: application/json" \
  -d '{{"question":"What is the protection class of the KD-210?","top_k":30}}'
curl -s -X POST localhost:8000/agent/runs -H "X-API-Key: dev-engineer-key" -H "Content-Type: application/json" \
  -d '{{"request":"Find a replacement for discontinued part KD-240"}}'     # waits for approval
curl -s -X POST localhost:8000/approvals/$APPROVAL_ID/approve -H "X-API-Key: dev-approver-key"   # a different user
```
More in [docs/API.md](docs/API.md). To use a real model set `LLM_PROVIDER=anthropic` and `ANTHROPIC_API_KEY` in `.env`
(prices in `config/pricing.yaml`; check model ids first), then `specbridge eval run --suite qa --provider anthropic --dry-run`.

## Evaluation results

Generated from `eval_results/`. Dev baseline (the gate reference): **`{BASE_ID}`**; test-split report: **`{TEST_ID}`**.
Rows marked *(fake)* come from the fake provider and only prove the pipeline works.

| metric | dev [95% CI] | test [95% CI] |
|---|---|---|
{TABLE}

What the experiments found (tables with run ids in [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md)): the **context header** on each chunk matters most (dev recall@5 0.77 vs 0.38 without it, hybrid); layout-aware chunking on its own is **not** distinguishable from fixed chunks *with* the header; **vector-only beat hybrid on every metric** (so it is now the default; hybrid's keyword half was also the unstable part); a cross-encoder reranker lifts top-1 quality a lot but costs ~800 ms and was made harmful by a bug the experiment exposed (fixed); no retrieval-score abstention threshold generalised from dev to test. A **clean checkout** failed the regression gate and exposed a reproducibility bug (tie order depended on random UUIDs); it is fixed and all experiments were re-measured. Extraction-model and retry-loop experiments, real-model QA accuracy and judge calibration are **not yet run** (needs an API key / a human).

## Limitations (summary)

Synthetic-data bias and small evaluation sets (wide intervals); real-datasheet labels are provisional; judge uncalibrated; no real-LLM results; no OCR; keyword search is Postgres FTS, not BM25; single node, synchronous design; mock ERP; static API keys; not deployed. Details and the production to-do list: [docs/LIMITATIONS.md](docs/LIMITATIONS.md).

## Project structure

```
specbridge/            application: api/ agent/ extraction/ ingestion/ retrieval/ qa/ llm/ eval/ db/ auth/ erp_client/ ui/
erp_mock/              mock ERP service (FastAPI + SQLite, fault injection)
corpus/                synthetic datasheet generator, real datasheet manifest + fetch
eval/                  datasets (qa, extraction, agent scenarios, judge calibration) and gate thresholds
eval_results/          committed run results (json + md) and baseline.json
experiments/           experiment configs
alembic/  docker/  config/  scripts/dev/  tests/ (unit, integration, e2e)
docs/                  ARCHITECTURE, EVALUATION, EXPERIMENTS, LIMITATIONS, DEPLOYMENT, RUNBOOK, API, WALKTHROUGH,
                       PROJECT_STORY, decisions/ (ADRs), changes/ (per-task notes), build-log/ (PROGRESS, JOURNAL)
```

Full specification: [SPECBRIDGE_SPEC.md](SPECBRIDGE_SPEC.md). Build history: [docs/build-log/](docs/build-log/JOURNAL.md).
