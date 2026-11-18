# SpecBridge build journal (append-only)

## 2026-11-18 — 0.1 Prerequisites, git, CLAUDE.md, build log
**Goal:** Check prerequisites and lay down project rules and logs.
**What I did:**
- Checked tools: Python 3.12 available via uv (system python is 3.14.7, project pins 3.12), uv 0.13.5, make 3.81, git 2.56, Docker CLI 29.8.1 + Compose v5.5.1.
- Docker daemon NOT running (socket missing) -> prerequisite blocker per Section 0.4.
- Existing local git repo (no commits, no remote), `.python-version`=3.12, stub `src/specbridge`.
- Wrote .gitignore, CLAUDE.md, PROGRESS.md, JOURNAL.md.
**Files changed:** .gitignore, CLAUDE.md, docs/build-log/*
**Commands run and outcome:** `docker ps` fail (daemon down); others pass.
**Tests:** n/a
**Problems:** Docker not running; asking user to start it.
**Decisions made:** none yet
**Deviations from spec:** none
**Next step:** user starts Docker, then continue with 0.2.

## 2026-11-18 13:00 — 0.2 Hook logger and settings
**Goal:** Claude Code hook script logging redacted tool calls to logs/dev, plus .claude/settings.json
**What I did:** Claude Code hook script logging redacted tool calls to logs/dev, plus .claude/settings.json
**Files changed:** scripts/dev/log_tool_call.py .claude/settings.json tests/unit/test_hook_logger.py
**Commands run and outcome:** make lint typecheck test (pass)
**Tests:** 3 passed (tests/unit/test_hook_logger.py: truncation, redaction, always exit 0)
**Eval results (if any):** n/a
**Problems and how I solved them:** none
**Decisions made:** none
**Deviations from spec:** none
**Next step:** next task in PROGRESS.md

## 2026-11-18 13:01 — 0.3 Tooling: pyproject, uv, ruff, mypy, pytest, Makefile
**Goal:** uv project with flat specbridge/ layout, ruff, strict mypy, pytest, pre-commit config, Makefile targets, .env.example
**What I did:** uv project with flat specbridge/ layout, ruff, strict mypy, pytest, pre-commit config, Makefile targets, .env.example
**Files changed:** pyproject.toml Makefile .pre-commit-config.yaml .env.example .dockerignore
**Commands run and outcome:** make lint typecheck test (pass)
**Tests:** uv sync ok; ruff/mypy clean
**Eval results (if any):** n/a
**Problems and how I solved them:** Code committed together with 0.2 in commit 59692d6 (batched staging); this commit records the task.
**Decisions made:** Flat layout specbridge/ at repo root instead of pre-initialised src/ layout (matches spec Section 4); uv_build module-root=''. Python pinned >=3.12,<3.13.
**Deviations from spec:** Python upper bound pinned <3.13 for dependency compatibility
**Next step:** next task in PROGRESS.md

## 2026-11-18 13:01 — 0.4 Config, logging, middleware, health endpoints
**Goal:** pydantic-settings config with fail-fast validation, structlog JSON logging with redaction, request-id middleware, error format, rate limiting, /health /ready /metrics
**What I did:** pydantic-settings config with fail-fast validation, structlog JSON logging with redaction, request-id middleware, error format, rate limiting, /health /ready /metrics
**Files changed:** specbridge/config.py logging_setup.py metrics.py errors.py api/*
**Commands run and outcome:** make lint typecheck test (pass)
**Tests:** tests/unit/test_config.py, test_logging.py, test_api_basic.py pass
**Eval results (if any):** n/a
**Problems and how I solved them:** Code committed together with 0.2 in commit 59692d6 (batched staging); this commit records the task.
**Decisions made:** none
**Deviations from spec:** none
**Next step:** next task in PROGRESS.md

## 2026-11-18 13:01 — 0.5 Postgres+pgvector, Alembic, initial migration
**Goal:** SQLAlchemy models for all Section 6 tables, docker-compose db service, Alembic env, migration 0001 with vector extension, HNSW and GIN indexes, generated tsvector
**What I did:** SQLAlchemy models for all Section 6 tables, docker-compose db service, Alembic env, migration 0001 with vector extension, HNSW and GIN indexes, generated tsvector
**Files changed:** specbridge/db/* alembic/* docker-compose.yml
**Commands run and outcome:** make lint typecheck test (pass)
**Tests:** integration test_migrations_up_down_up passes against testcontainers pgvector
**Eval results (if any):** n/a
**Problems and how I solved them:** Code committed together with 0.2 in commit 59692d6 (batched staging); this commit records the task.
**Decisions made:** chunks has extra search_text column so the context header is FTS-indexed while content stays clean for citations
**Deviations from spec:** added chunks.search_text column (spec: content_tsv generated from content; header must be indexed per 7.3)
**Next step:** next task in PROGRESS.md

## 2026-11-18 13:01 — 0.6 LLM provider layer
**Goal:** LLMProvider protocol; Fake/Anthropic/Bedrock providers; tenacity retries; pricing.yaml (prices verified from platform.claude.com 2026-11-18); budget guard; SQLite response cache; usage accounting; forced-tool structured output with one retry
**What I did:** LLMProvider protocol; Fake/Anthropic/Bedrock providers; tenacity retries; pricing.yaml (prices verified from platform.claude.com 2026-11-18); budget guard; SQLite response cache; usage accounting; forced-tool structured output with one retry
**Files changed:** specbridge/llm/* specbridge/prompts/__init__.py config/pricing.yaml
**Commands run and outcome:** make lint typecheck test (pass)
**Tests:** tests/unit/test_llm.py 10 passed; integration llm_calls row + db budget
**Eval results (if any):** n/a
**Problems and how I solved them:** Code committed together with 0.2 in commit 59692d6 (batched staging); this commit records the task. Test bug: 1M tokens exceeded Haiku long-context threshold; fixed the test not the code.
**Decisions made:** LLMService wraps providers; fake provider costs 0; unknown priced model raises
**Deviations from spec:** none
**Next step:** next task in PROGRESS.md

## 2026-11-18 13:01 — 0.7 Auth, RBAC, audit
**Goal:** API key store with constant-time compare, permission matrix, FastAPI require() dependency, append-only audit log, denials audited in separate transaction
**What I did:** API key store with constant-time compare, permission matrix, FastAPI require() dependency, append-only audit log, denials audited in separate transaction
**Files changed:** specbridge/auth/* audit.py api/deps.py
**Commands run and outcome:** make lint typecheck test (pass)
**Tests:** tests/unit/test_auth.py pass; integration test_audit_and_denied_survive
**Eval results (if any):** n/a
**Problems and how I solved them:** Code committed together with 0.2 in commit 59692d6 (batched staging); this commit records the task. Denial audit uses its own session so the request rollback cannot drop it.
**Decisions made:** none
**Deviations from spec:** none
**Next step:** M1.1 synthetic datasheet generator

## 2026-11-18 13:05 — 1.1 Synthetic datasheet generator and ground truth
**Goal:** Deterministic generator (seed 42): 3 fictional vendors, 45 parts + 5 rev1.1 + 1 prompt-injection datasheet = 51 PDFs in 4 layout families with format variety; ground truth with per-field evidence pages, lifecycle, replacement candidates; shared candidate rule in specbridge/extraction/fields.py
**What I did:** Deterministic generator (seed 42): 3 fictional vendors, 45 parts + 5 rev1.1 + 1 prompt-injection datasheet = 51 PDFs in 4 layout families with format variety; ground truth with per-field evidence pages, lifecycle, replacement candidates; shared candidate rule in specbridge/extraction/fields.py
**Files changed:** corpus/synthetic/* specbridge/extraction/fields.py eval/datasets/extraction_synthetic.jsonl tests/unit/test_corpus.py
**Commands run and outcome:** make lint typecheck test (pass)
**Tests:** tests/unit/test_corpus.py 8 passed (counts, determinism, revisions, scenario invariants, injection doc)
**Eval results (if any):** n/a
**Problems and how I solved them:** Initial hash-based split gave 23/28; replaced with rank-based split. Ruff E501 disabled (formatter wraps; long data strings).
**Decisions made:** Hand-crafted override parts (orphans KD-310/NS-PRS-3400, constraint-scenario NS-IND-1200..1208, injection scenario AL-DIO-101/103/199) guarantee agent scenarios are well-defined; 60/40 dev/test split by sorted part number; GT also stores replacement_candidates
**Deviations from spec:** none
**Next step:** next task in PROGRESS.md

## 2026-11-18 13:07 — 1.2 Real datasheet manifest, fetch script, provisional labels
**Goal:** 9 real public datasheets (ifm, Omron, Lantronix, Wachendorff, wenglor, Bernstein) located via web search, verified as PDFs, listed in corpus/real/manifest.yaml with sha256; fetch.py re-downloads and verifies; draft labels in eval/datasets/extraction_real.jsonl all verified_by_human=false
**What I did:** 9 real public datasheets (ifm, Omron, Lantronix, Wachendorff, wenglor, Bernstein) located via web search, verified as PDFs, listed in corpus/real/manifest.yaml with sha256; fetch.py re-downloads and verifies; draft labels in eval/datasets/extraction_real.jsonl all verified_by_human=false
**Files changed:** corpus/real/* eval/datasets/extraction_real.jsonl
**Commands run and outcome:** make lint typecheck test (pass)
**Tests:** fetch.py run: 9 verified, 0 problems (network, manual run; not part of the test suite)
**Eval results (if any):** n/a
**Problems and how I solved them:** Baumer/Parker/ifm AL2301/Mean Well/ipf blocked automated download (403); excluded. Multi-model catalogs (Leadshine, siol hubs, P+F parameter sheets) excluded as unsuitable for single-component labels.
**Decisions made:** Where a datasheet gives only nominal or ambiguous values the label is null or the highest rating, documented in each record's notes field
**Deviations from spec:** 9 real datasheets instead of 10-20 (logged in Needs user)
**Next step:** next task in PROGRESS.md

## 2026-11-18 13:08 — 1.4 ERP mock service, seed, fault injection
**Goal:** Separate FastAPI+SQLite mock ERP: parts, change requests, mandatory Idempotency-Key (replay same body, 409 on different body), fault injection (failure rate, fail first N writes, latency) via env and /_admin/faults, seed from synthetic ground truth, structured request logs
**What I did:** Separate FastAPI+SQLite mock ERP: parts, change requests, mandatory Idempotency-Key (replay same body, 409 on different body), fault injection (failure rate, fail first N writes, latency) via env and /_admin/faults, seed from synthetic ground truth, structured request logs
**Files changed:** erp_mock/* tests/unit/test_erp_mock.py
**Commands run and outcome:** make lint typecheck test (pass)
**Tests:** tests/unit/test_erp_mock.py 6 passed
**Eval results (if any):** n/a
**Problems and how I solved them:** none
**Decisions made:** Fault injection applies to write calls only so lookups still work when the ERP is 'down for writes' (agent scenarios 8/9); failed (503) writes never record an idempotency key
**Deviations from spec:** none
**Next step:** next task in PROGRESS.md

## 2026-11-18 13:09 — 1.3 QA dataset generator and dataset validation
**Goal:** 108 QA items generated programmatically from ground truth (factual 35, table_lookup 20, cross_doc 15, revision 8, unanswerable 15, injection 5, open 10), 60/40 dev/test; loader + validate_datasets()
**What I did:** 108 QA items generated programmatically from ground truth (factual 35, table_lookup 20, cross_doc 15, revision 8, unanswerable 15, injection 5, open 10), 60/40 dev/test; loader + validate_datasets()
**Files changed:** corpus/synthetic/qa_dataset.py specbridge/eval/datasets.py eval/datasets/qa.jsonl tests/unit/test_datasets.py
**Commands run and outcome:** make lint typecheck test (pass)
**Tests:** tests/unit/test_datasets.py 6 passed; validate_datasets() returns no problems
**Eval results (if any):** n/a
**Problems and how I solved them:** none
**Decisions made:** Extra item fields beyond spec: expect_abstain, forbidden (injection), superseded_value, unit/tolerance. Unanswerable: 10 absent-attribute, 3 nonexistent part, 2 null-field questions
**Deviations from spec:** none
**Next step:** next task in PROGRESS.md

## 2026-11-18 13:13 — 2.1 Parser, chunking, embeddings, ingestion pipeline and CLI
**Goal:** PyMuPDF parser (blocks+bboxes, tables via find_tables with word-spaced cell text, headings, part-number/revision/vendor detection); fixed and layout chunking with context headers kept out of displayed content; embedder wrapper (bge-small, offline hash embedder for tests); idempotent ingestion with per-index chunks, revision linking, failure recording; 'specbridge ingest' CLI
**What I did:** PyMuPDF parser (blocks+bboxes, tables via find_tables with word-spaced cell text, headings, part-number/revision/vendor detection); fixed and layout chunking with context headers kept out of displayed content; embedder wrapper (bge-small, offline hash embedder for tests); idempotent ingestion with per-index chunks, revision linking, failure recording; 'specbridge ingest' CLI
**Files changed:** specbridge/ingestion/* specbridge/cli.py tests/unit/test_chunking.py tests/integration/test_ingestion.py
**Commands run and outcome:** make lint typecheck test (pass)
**Tests:** unit 59 passed total (test_chunking.py 9); integration 8 passed (idempotency, extra index, reingest, revision linking, failure isolation, upload validation). Real run: 'specbridge ingest data/corpus' -> 60 files, 0 failed, 264 chunks (58 tables), 33s incl. model load
**Eval results (if any):** n/a
**Problems and how I solved them:** find_tables().extract() dropped spaces in cells -> rebuilt cell text with page.get_textbox per cell; heading-only chunks (vendor banner) merged into following section; IO-Link 'revision 1.1' was mis-detected as datasheet revision -> case-sensitive Revision + lookbehind
**Decisions made:** Document is skipped only if chunks exist for the requested index (lets experiments build separate indexes from one document row); failed parses recorded as status=failed rows
**Deviations from spec:** none
**Next step:** next task in PROGRESS.md

## 2026-11-18 13:14 — 2.2 Retrieval: vector, keyword, hybrid RRF, optional rerank
**Goal:** pgvector cosine search, Postgres FTS keyword search (websearch_to_tsquery, OR-combined content words, 'simple' config), RRF fusion (k=60, top 30 each), optional cross-encoder rerank of fused top 20; per-call mode/top_k/rerank/include_superseded/index; vector similarity always computed as abstention signal
**What I did:** pgvector cosine search, Postgres FTS keyword search (websearch_to_tsquery, OR-combined content words, 'simple' config), RRF fusion (k=60, top 30 each), optional cross-encoder rerank of fused top 20; per-call mode/top_k/rerank/include_superseded/index; vector similarity always computed as abstention signal
**Files changed:** specbridge/retrieval/* tests/unit/test_retrieval_units.py tests/integration/test_retrieval.py
**Commands run and outcome:** make lint typecheck test (pass)
**Tests:** unit test_retrieval_units 4 passed; integration test_retrieval 9 passed (3 modes, exact part number, RRF scores, revision filter, index isolation, rerank, bad mode)
**Eval results (if any):** n/a
**Problems and how I solved them:** none
**Decisions made:** Natural-language questions are turned into an OR query of content words (stop words dropped); AND semantics of websearch_to_tsquery would match nothing. Abstention uses best vector cosine similarity regardless of mode (RRF scores are rank-based and not calibratable)
**Deviations from spec:** none
**Next step:** next task in PROGRESS.md

## 2026-11-18 13:16 — 2.3 Q&A service with citation verification and abstention
**Goal:** Versioned prompt qa_answer.v1 (sources untrusted, verbatim quotes), sources wrapped in <source> tags with closing-tag escaping, forced submit_answer tool, rapidfuzz citation verification (partial_ratio>=90 after dash/ellipsis/pipe normalisation), dropped invalid citations, unsupported-answer blocking, retrieval-score abstention without an LLM call, query_logs row; deterministic extractive fake responder for pipeline checks
**What I did:** Versioned prompt qa_answer.v1 (sources untrusted, verbatim quotes), sources wrapped in <source> tags with closing-tag escaping, forced submit_answer tool, rapidfuzz citation verification (partial_ratio>=90 after dash/ellipsis/pipe normalisation), dropped invalid citations, unsupported-answer blocking, retrieval-score abstention without an LLM call, query_logs row; deterministic extractive fake responder for pipeline checks
**Files changed:** specbridge/qa/* specbridge/prompts/qa_answer.v1.md specbridge/llm/fake_handlers.py tests/unit/test_citations.py tests/integration/test_qa.py
**Commands run and outcome:** make lint typecheck test (pass)
**Tests:** unit test_citations 6 passed; integration test_qa 7 passed (valid citation + query log, invalid dropped, unsupported blocked, model-unanswerable, low-score abstain w/o LLM call, injection text only inside source tags, fake end-to-end). Whole suite 93 passed
**Eval results (if any):** n/a
**Problems and how I solved them:** My first tests quoted the part number, but table chunks keep the context header in metadata (by design) so the quote was correctly rejected; tests now quote real S1 text
**Decisions made:** Fake QA responder is extractive and only a pipeline check; its accuracy numbers are not a quality benchmark
**Deviations from spec:** none
**Next step:** next task in PROGRESS.md

## 2026-11-18 13:17 — 2.4 API routes: documents, query, highlighted page images
**Goal:** POST/GET /documents (magic-byte + size checks, bounded read, audit), POST /query (Pydantic validated, whitelisted modes), GET page image PNG with cited bboxes highlighted and cached under data/cache/pages; shared integration fixtures (TestClient with fake LLM, isolated DATA_DIR)
**What I did:** POST/GET /documents (magic-byte + size checks, bounded read, audit), POST /query (Pydantic validated, whitelisted modes), GET page image PNG with cited bboxes highlighted and cached under data/cache/pages; shared integration fixtures (TestClient with fake LLM, isolated DATA_DIR)
**Files changed:** specbridge/api/routers/{documents,query}.py specbridge/api/main.py tests/integration/conftest.py tests/integration/test_api_docs_query.py
**Commands run and outcome:** make lint typecheck test (pass)
**Tests:** integration test_api_docs_query 8 passed (401/403 + audited denial, upload/list/get/idempotent, non-PDF and oversize rejected, query + highlighted image differs from plain + cache hit, validation, abstain on empty corpus)
**Eval results (if any):** n/a
**Problems and how I solved them:** none
**Decisions made:** none
**Deviations from spec:** none
**Next step:** next task in PROGRESS.md

## 2026-11-18 13:19 — 2.5 UI: login, ask, documents, source page
**Goal:** Jinja2 server-rendered UI: /ui/login (API key -> signed httponly SameSite=Strict cookie holding user+role), /ui/ask with numbered citations linking to /ui/source (quote + highlighted page image), /ui/documents; same RBAC; cookie-auth page image route; plain CSS
**What I did:** Jinja2 server-rendered UI: /ui/login (API key -> signed httponly SameSite=Strict cookie holding user+role), /ui/ask with numbered citations linking to /ui/source (quote + highlighted page image), /ui/documents; same RBAC; cookie-auth page image route; plain CSS
**Files changed:** specbridge/api/routers/ui.py specbridge/ui/* tests/integration/test_ui.py
**Commands run and outcome:** make lint typecheck test (pass)
**Tests:** integration test_ui 7 passed (redirect when logged out, bad key, forged cookie, cookie flags, full ask->source->PNG flow, HTML escaping, logout, static). Manual check: real uvicorn run against the ingested dev DB, highlighted page PNG inspected visually
**Eval results (if any):** n/a
**Problems and how I solved them:** find_tables bbox is narrower than the full drawn grid so the highlight covers the table's text extent, not its full width (noted for LIMITATIONS)
**Decisions made:** Page images need cookie auth in the UI because browsers cannot send X-API-Key on <img>; added /ui/page route sharing page_image_bytes() with the API
**Deviations from spec:** none
**Next step:** next task in PROGRESS.md

## 2026-11-18 13:22 — 2.6 Eval core: stats, metrics, judge, runner, compare, CLI
**Goal:** Wilson CIs and noise flags; answer matching (numeric with units/decimal commas, sets with aliases, contains, exact), retrieval recall@k/MRR by type, QA accuracy/abstention P&R/injection resistance/citation precision+coverage/stale-revision rate; LLM judge (uncalibrated); runner with cost estimate and abort, result json+md with dataset hashes, config, models, prompt versions; compare; 'specbridge eval run|compare|set-baseline|validate-datasets'
**What I did:** Wilson CIs and noise flags; answer matching (numeric with units/decimal commas, sets with aliases, contains, exact), retrieval recall@k/MRR by type, QA accuracy/abstention P&R/injection resistance/citation precision+coverage/stale-revision rate; LLM judge (uncalibrated); runner with cost estimate and abort, result json+md with dataset hashes, config, models, prompt versions; compare; 'specbridge eval run|compare|set-baseline|validate-datasets'
**Files changed:** specbridge/eval/{stats,metrics,judge,runner,compare,suites_extra}.py specbridge/cli.py specbridge/prompts/judge_usefulness.v1.md tests/unit/test_eval_*.py tests/integration/test_eval_run.py
**Commands run and outcome:** make lint typecheck test (pass)
**Tests:** unit: test_eval_metrics 17, test_eval_runner_units 5; integration test_eval_run 5 (retrieval deterministic, modes differ, fake QA pipeline, missing index, paid provider without key blocked)
**Eval results (if any):** n/a
**Problems and how I solved them:** none
**Decisions made:** Noise flag: significant=disjoint 95% CIs, weak=<50% overlap of narrower CI, within noise=>=50%. Retrieval hit = chunk from an expected doc_key AND expected page. CLI keeps full JSON logs in logs/app.jsonl and only warnings on stdout unless -v
**Deviations from spec:** none
**Next step:** next task in PROGRESS.md

## 2026-11-18 13:22 — 2.7 First retrieval baseline and QA pipeline check
**Goal:** Retrieval eval on dev (hybrid, layout chunks, bge-small) set as eval_results/baseline.json; QA suite run with the fake provider as a pipeline check; real QA run blocked (no API key)
**What I did:** Retrieval eval on dev (hybrid, layout chunks, bge-small) set as eval_results/baseline.json; QA suite run with the fake provider as a pipeline check; real QA run blocked (no API key)
**Files changed:** eval_results/* docs/build-log/PROGRESS.md
**Commands run and outcome:** make lint typecheck test (pass)
**Tests:** no new tests; runs recorded in eval_results/
**Eval results (if any):** Retrieval baseline run 20261118-132236_7ca7287_initial-retrieval (dev, n=56): see eval_results/*initial-retrieval.md. Fake-provider QA run 20261118-132241_7ca7287_qa-fake-pipeline is a PIPELINE CHECK ONLY (extractive responder, constant judge) - not a quality result. Real QA run: blocked: needs API key
**Problems and how I solved them:** none
**Decisions made:** none
**Deviations from spec:** none
**Next step:** next task in PROGRESS.md

## 2026-11-18 13:26 — 3.1 Extraction schema, extractor, normalisation, validators, retry loop
**Goal:** ComponentSpec schema (FieldValue with page+quote, no confidence field); pint-based unit normalisation (decimal commas, en-dash and ellipsis ranges, mA/kW/kg, IP forms, interface/cert alias maps); deterministic validators (required, min<=max, plausibility, IP regex, evidence quote on cited page >=85, numbers supported by quote, category warnings); extractor with page selection, untrusted-data page tags, one retry with errors, status validated|pending_review; rule-based fake extractor
**What I did:** ComponentSpec schema (FieldValue with page+quote, no confidence field); pint-based unit normalisation (decimal commas, en-dash and ellipsis ranges, mA/kW/kg, IP forms, interface/cert alias maps); deterministic validators (required, min<=max, plausibility, IP regex, evidence quote on cited page >=85, numbers supported by quote, category warnings); extractor with page selection, untrusted-data page tags, one retry with errors, status validated|pending_review; rule-based fake extractor
**Files changed:** specbridge/extraction/* specbridge/prompts/extraction.v1.md specbridge/llm/usage.py tests/unit/test_units.py tests/unit/test_extraction.py
**Commands run and outcome:** make lint typecheck test (pass)
**Tests:** unit: test_units 56, test_extraction 13 (normalisation, every validator rule, retry loop success/failure, page selection, escaping). Whole unit suite green
**Eval results (if any):** n/a
**Problems and how I solved them:** Sign regex char class '[+-–]' formed a range and swallowed digits; empty-string-in-str bug made a leading minus lose its sign. Both found by tests and fixed
**Decisions made:** Per-call model override in LLMService.structured() instead of mutating shared settings. A quote with a one-digit difference fuzzy-matches, so a separate number-in-quote check is required (validated records can still be semantically wrong; measured as precision of validated records in 3.4)
**Deviations from spec:** none
**Next step:** next task in PROGRESS.md

## 2026-11-18 13:27 — 3.2 Review queue, approval and ERP push with idempotency
**Goal:** ERP client (tenacity retries on 5xx/timeouts, mandatory idempotency keys); review service: audited field edits (old/new), re-validation on save, mark reviewed, approve (unreviewed pending items blocked), reject, push with key=sha256(extraction_id+schema_version) and retryable push_failed
**What I did:** ERP client (tenacity retries on 5xx/timeouts, mandatory idempotency keys); review service: audited field edits (old/new), re-validation on save, mark reviewed, approve (unreviewed pending items blocked), reject, push with key=sha256(extraction_id+schema_version) and retryable push_failed
**Files changed:** specbridge/erp_client/client.py specbridge/extraction/review.py tests/integration/test_extraction_flow.py
**Commands run and outcome:** make lint typecheck test (pass)
**Tests:** integration test_extraction_flow 7 passed: extract->validated, validation failure->review->edit->approve->push, edit type/unknown-field guards, reject/state guards, transient ERP failures -> exactly one ERP write, permanent failure -> push_failed -> retry -> exactly one write, audit order error then allowed
**Eval results (if any):** n/a
**Problems and how I solved them:** none
**Decisions made:** Approving a pending_review extraction requires that a human marked it reviewed; no four-eyes rule for extraction approvals (spec requires it only for agent change requests); pushing an already-pushed extraction is a no-op
**Deviations from spec:** none
**Next step:** next task in PROGRESS.md

## 2026-11-18 13:29 — 3.3 Extraction API routes and review UI
**Goal:** POST/GET/PATCH /extractions, approve/reject/push with RBAC (engineer edits; approver approves/pushes), consistent errors; /ui/review queue + detail page with value, evidence quote, page link, validation errors, editable fields, role-aware buttons
**What I did:** POST/GET/PATCH /extractions, approve/reject/push with RBAC (engineer edits; approver approves/pushes), consistent errors; /ui/review queue + detail page with value, evidence quote, page link, validation errors, editable fields, role-aware buttons
**Files changed:** specbridge/api/routers/extractions.py specbridge/api/routers/ui.py specbridge/ui/templates/review*.html tests/integration/test_api_extractions.py
**Commands run and outcome:** make lint typecheck test (pass)
**Tests:** integration test_api_extractions 4 passed: role matrix incl. audited denials, push exactly once, PATCH revalidation, push failure then retry, UI review flow
**Eval results (if any):** n/a
**Problems and how I solved them:** UI edit handler would have blanked fields missing from a partial form post; now only submitted fields are edited
**Decisions made:** none
**Deviations from spec:** none
**Next step:** next task in PROGRESS.md
