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

## 2026-11-18 13:30 — 3.4 Extraction eval suite
**Goal:** Suite scoring per-field and micro P/R/F1 (1% numeric tolerance, null handling, set comparison for lists), evidence validity rate, % auto-validated vs needing review, precision of validated records (doc-level and field-level), attempts, cost per document; synthetic labels + provisional real labels reported separately; config options model/retry/include_real for experiments; compact markdown report
**What I did:** Suite scoring per-field and micro P/R/F1 (1% numeric tolerance, null handling, set comparison for lists), evidence validity rate, % auto-validated vs needing review, precision of validated records (doc-level and field-level), attempts, cost per document; synthetic labels + provisional real labels reported separately; config options model/retry/include_real for experiments; compact markdown report
**Files changed:** specbridge/extraction/eval_suite.py specbridge/eval/runner.py tests/unit/test_extraction_eval.py tests/integration/test_eval_run.py eval_results/*extraction-fake-pipeline.*
**Commands run and outcome:** make lint typecheck test (pass)
**Tests:** unit test_extraction_eval 4; integration test_eval_run 7 (adds extraction suite + config options)
**Eval results (if any):** Fake-provider extraction run 20261118-132949_2cf9cda_extraction-fake-pipeline (dev, 33 synthetic docs): PIPELINE CHECK ONLY - the 'model' is a rule-based regex extractor. Real extraction run: blocked: needs API key
**Problems and how I solved them:** none
**Decisions made:** none
**Deviations from spec:** none
**Next step:** next task in PROGRESS.md

## 2026-11-18 13:41 — 4.1 Agent state machine, tools, allowlists, limits
**Goal:** Explicit persisted state machine (RECEIVED..DONE, REJECTED/FAILED/ESCALATED) with transition table; per-state tool allowlists (write tool only in COMMITTING and only with an approved approval row); deterministic search_parts via parameterised SQLAlchemy (category, temp range, voltage overlap, IP>=, constraints, ERP lifecycle exclusion, max 10); COMPARE loop with max 3 evidence calls, ranking validation (candidate whitelist, citation verification, uncited claims removed, escalate if no verified evidence); max 6 LLM calls; 120s step limit; untrusted evidence wrapped as data
**What I did:** Explicit persisted state machine (RECEIVED..DONE, REJECTED/FAILED/ESCALATED) with transition table; per-state tool allowlists (write tool only in COMMITTING and only with an approved approval row); deterministic search_parts via parameterised SQLAlchemy (category, temp range, voltage overlap, IP>=, constraints, ERP lifecycle exclusion, max 10); COMPARE loop with max 3 evidence calls, ranking validation (candidate whitelist, citation verification, uncited claims removed, escalate if no verified evidence); max 6 LLM calls; 120s step limit; untrusted evidence wrapped as data
**Files changed:** specbridge/agent/{states,permissions,models,tools,runner,fake}.py specbridge/prompts/agent_*.md tests/unit/test_agent_units.py tests/integration/test_agent_runner.py
**Commands run and outcome:** make lint typecheck test (pass)
**Tests:** unit test_agent_units 12; integration test_agent_runner 9 (write guard, step/audit persistence, evidence cap, LLM-call cap -> ESCALATED, hallucinated parts/uncited claims dropped, no-evidence escalation, step timeout, explicit resume)
**Eval results (if any):** n/a
**Problems and how I solved them:** Implemented together with 4.2 in one working tree; this commit holds both, 4.2 records its own behaviour.
**Decisions made:** Candidate must have >=1 verified claim or the run ESCALATES (never propose on unverified rationale). Agent scenarios seed approved extractions from ground truth so they test the agent, not the extractor. ADR-0002 will cover state machine vs framework
**Deviations from spec:** none
**Next step:** next task in PROGRESS.md

## 2026-11-18 13:41 — 4.2 Approval flow, four-eyes, commit retries/idempotency, explicit resume
**Goal:** approvals row created in AWAITING_APPROVAL (idempotent); POST /approvals/{id}/approve|reject; four-eyes rule (requester cannot decide, denial audited in its own transaction); COMMITTING uses idempotency key = run id with tenacity retries (3 attempts) -> FAILED(retryable) -> POST /agent/runs/{id}/retry; resume after crash via AgentRunner.resume; ERP fault 'lose_response_first_n' (write executes, response lost) added to prove idempotency
**What I did:** approvals row created in AWAITING_APPROVAL (idempotent); POST /approvals/{id}/approve|reject; four-eyes rule (requester cannot decide, denial audited in its own transaction); COMMITTING uses idempotency key = run id with tenacity retries (3 attempts) -> FAILED(retryable) -> POST /agent/runs/{id}/retry; resume after crash via AgentRunner.resume; ERP fault 'lose_response_first_n' (write executes, response lost) added to prove idempotency
**Files changed:** specbridge/api/routers/agent.py specbridge/agent/runner.py erp_mock/* specbridge/audit.py
**Commands run and outcome:** make lint typecheck test (pass)
**Tests:** integration test_agent_runner approval/four-eyes/double-decision + resume tests; scenario S08/S09/S13/S15. Mutation checks performed manually: removing allowlist entry, four-eyes check, discontinued filter, or stable idempotency key each makes a scenario FAIL (see journal)
**Eval results (if any):** n/a
**Problems and how I solved them:** First harness version did not detect a random (non-stable) idempotency key because the mock ERP only stored successful writes; added lose_response_first_n fault and scenario S15 so a lost-response + explicit-retry sequence would create a duplicate without a stable key
**Decisions made:** none
**Deviations from spec:** none
**Next step:** next task in PROGRESS.md

## 2026-11-18 13:42 — 4.3 Agent API routes and UI: approvals page and run timeline
**Goal:** POST/GET /agent/runs, steps, retry; GET /approvals, approve/reject; UI /ui/runs (start form + list), /ui/runs/{id} timeline with tool calls, status, latency, outputs and state transitions, /ui/approvals with evidence quotes and role-aware approve/reject, retry button for failed commits
**What I did:** POST/GET /agent/runs, steps, retry; GET /approvals, approve/reject; UI /ui/runs (start form + list), /ui/runs/{id} timeline with tool calls, status, latency, outputs and state transitions, /ui/approvals with evidence quotes and role-aware approve/reject, retry button for failed commits
**Files changed:** specbridge/api/routers/agent.py specbridge/api/routers/ui.py specbridge/ui/templates/{approvals,runs,run_detail}.html tests/integration/test_api_agent_ui.py
**Commands run and outcome:** make lint typecheck test (pass)
**Tests:** integration test_api_agent_ui 4 passed (RBAC incl. viewer 403, engineer cannot approve, requester-approver four-eyes 403, double decision 409, failed commit then retry endpoint, UI flow)
**Eval results (if any):** n/a
**Problems and how I solved them:** none
**Decisions made:** none
**Deviations from spec:** none
**Next step:** next task in PROGRESS.md

## 2026-11-18 13:43 — 4.4 Agent scenario eval suite
**Goal:** All scenarios (14 required + 1 extra: lost responses then retry) executed through the real HTTP API against a seeded environment in an ephemeral database; per-scenario expectations plus global invariants (ERP change requests == DONE runs, DONE only with an approved approval); safety scenarios S05,S06,S07,S10,S11,S12 reported separately; wired into 'specbridge eval run --suite agent'
**What I did:** All scenarios (14 required + 1 extra: lost responses then retry) executed through the real HTTP API against a seeded environment in an ephemeral database; per-scenario expectations plus global invariants (ERP change requests == DONE runs, DONE only with an approved approval); safety scenarios S05,S06,S07,S10,S11,S12 reported separately; wired into 'specbridge eval run --suite agent'
**Files changed:** specbridge/agent/{scenarios,eval_suite}.py specbridge/db/admin.py specbridge/db/session.py eval/datasets/agent_scenarios.yaml eval_results/*agent-scenarios-fake.*
**Commands run and outcome:** make lint typecheck test (pass)
**Tests:** integration test_eval_run agent suite (hermetic, DB dropped afterwards); test_agent_scenarios 18
**Eval results (if any):** Run 20261118-134227_d77cbfa_agent-scenarios-fake (fake provider): 15/15 scenarios pass, 6/6 safety scenarios pass. Live-LLM agent run: blocked: needs API key
**Problems and how I solved them:** none
**Decisions made:** Scenarios are executed with the FakeProvider by design: they test code-enforced safety (allowlists, approval gate, four-eyes, idempotency) with scripted adversarial model behaviour, which a real LLM cannot reproduce on demand
**Deviations from spec:** none
**Next step:** next task in PROGRESS.md

## 2026-11-18 13:44 — 5.1 Eval gate, thresholds and make gate-retrieval
**Goal:** eval/thresholds.yaml per spec (+ a latency noise floor); 'specbridge eval gate' compares candidate vs baseline (recall@5, MRR, QA accuracy/citation precision/abstention recall, extraction micro-F1, p95 latency, cost per 100 queries, agent safety scenarios), refuses incomparable runs (split or relevant dataset hash mismatch), exits 1 on regressions and 2 on errors; Makefile gate-retrieval uses the latest 'ci'-tagged run
**What I did:** eval/thresholds.yaml per spec (+ a latency noise floor); 'specbridge eval gate' compares candidate vs baseline (recall@5, MRR, QA accuracy/citation precision/abstention recall, extraction micro-F1, p95 latency, cost per 100 queries, agent safety scenarios), refuses incomparable runs (split or relevant dataset hash mismatch), exits 1 on regressions and 2 on errors; Makefile gate-retrieval uses the latest 'ci'-tagged run
**Files changed:** specbridge/eval/gate.py eval/thresholds.yaml experiments/deliberate-regression-keyword.yaml specbridge/eval/datasets.py specbridge/cli.py Makefile tests/unit/test_gate.py
**Commands run and outcome:** make lint typecheck test (pass)
**Tests:** unit test_gate 21 passed (every threshold boundary, improvements never fail, noise floor, suite filter, incomparable runs, CLI exit codes 0/1/2)
**Eval results (if any):** Deliberate regression proof: baseline 20261118-132236_7ca7287_initial-retrieval vs keyword-only run 20261118-134429_9ae7ca4_deliberate-regression (dev): recall@5 0.911 -> 0.536, MRR 0.684 -> 0.315, gate exit code 1. Clean re-run 20261118-134352_9ae7ca4_ci: gate PASSED (identical metrics)
**Problems and how I solved them:** The gate first refused the baseline because an unrelated dataset (agent_scenarios.yaml) had changed; comparability is now judged only on the datasets a suite depends on
**Decisions made:** Added ops_noise_floor (20 ms) because p95 latency of a ~25 ms retrieval stage varies by more than 25% between runs on the same machine
**Deviations from spec:** extra threshold key ops_noise_floor not in the spec
**Next step:** next task in PROGRESS.md

## 2026-11-18 13:51 — 5.2 Experiments 1-4 and 7 (5-6 blocked: needs API key); docs/EXPERIMENTS.md
**Goal:** Retrieval-side experiments run on dev and confirmed once on test: chunking (+ a fixed+header control), retrieval mode, reranker (found and fixed a real bug: reranker must see the context header), context header, abstention-threshold calibration (new calibration suite). Tables in docs/EXPERIMENTS.md are generated from run files
**What I did:** Retrieval-side experiments run on dev and confirmed once on test: chunking (+ a fixed+header control), retrieval mode, reranker (found and fixed a real bug: reranker must see the context header), context header, abstention-threshold calibration (new calibration suite). Tables in docs/EXPERIMENTS.md are generated from run files
**Files changed:** specbridge/eval/{calibration,experiments}.py experiments/*.yaml docs/EXPERIMENTS.md eval_results/*exp* specbridge/retrieval/service.py specbridge/ingestion/chunking.py specbridge/cli.py
**Commands run and outcome:** make lint typecheck test (pass)
**Tests:** unit test_calibration 2; integration test_retrieval (reranker input includes context header) ; test_chunking (fixed+header)
**Eval results (if any):** See docs/EXPERIMENTS.md (all run ids). Key results (dev, n=56): header on/off recall@5 0.911 vs 0.429; layout vs fixed 0.911 vs 0.643 but fixed+header 0.857 (within noise of layout); hybrid 0.911 vs vector 0.875 (within noise); rerank fixed: recall@1 0.875 vs 0.554 at ~800 ms; no abstention threshold generalises to test. Exp 5/6: blocked: needs API key
**Problems and how I solved them:** First reranker run was far worse than no reranker (recall@5 0.589): it scored content without the context header. Fixed, regression-tested, and both runs are kept in the record. Experiment 1 was confounded (header vs layout); added a fixed+header control, which showed the header explains the gain
**Decisions made:** Defaults unchanged: layout+header, hybrid, rerank off, ABSTAIN_MIN_SCORE=0.0. 'chunk strategy fixed' now accepts a context header too (CLI default: layout on, fixed off)
**Deviations from spec:** none; 5-6 blocked as allowed by 0.4
**Next step:** next task in PROGRESS.md

## 2026-11-18 13:52 — 5.3 Final defaults confirmed; full dev baseline and test-split report
**Goal:** Defaults confirmed unchanged by the experiments. Full evaluation (retrieval, QA, extraction, agent; fake provider for LLM suites) run on dev and set as eval_results/baseline.json (the gate reference), and on test as the final report; make eval-retrieval gate-retrieval passes against the new baseline
**What I did:** Defaults confirmed unchanged by the experiments. Full evaluation (retrieval, QA, extraction, agent; fake provider for LLM suites) run on dev and set as eval_results/baseline.json (the gate reference), and on test as the final report; make eval-retrieval gate-retrieval passes against the new baseline
**Files changed:** eval_results/baseline.json eval_results/*baseline-dev-all.* eval_results/*final-test-all.* docs/decisions/DECISION_LOG.md
**Commands run and outcome:** make lint typecheck test (pass)
**Tests:** n/a (evaluation runs); gate PASSED for the baseline run itself and for a fresh 'ci' retrieval run
**Eval results (if any):** Baseline (dev, set via 'eval set-baseline'): 20261118-135200_e64a52b_baseline-dev-all. Final test-split report: 20261118-135217_e64a52b_final-test-all (retrieval recall@5 0.865 n=37; agent 15/15 scenarios, 6/6 safety; QA/extraction numbers are fake-provider pipeline checks, NOT model quality). Real-model QA/extraction/agent runs: blocked: needs API key
**Problems and how I solved them:** none
**Decisions made:** Baseline is the dev run because the CI gate runs on dev; test is reported once, never gated
**Deviations from spec:** Spec says run the full test-split evaluation then set the final baseline; the baseline is the dev run so that gating stays comparable and never touches test. The test-split full run exists as a separate final report
**Next step:** next task in PROGRESS.md

## 2026-11-18 13:56 — 6.1 Rate limiting, upload hardening, redaction tests, pip-audit
**Goal:** Per-API-key moving-window rate limit middleware (limits library; /health /ready /metrics exempt; error format with request id); upload hardening: magic bytes, size limit with bounded read, filename sanitisation, page-count cap (400); redaction tests (log values, headers, LLM payload log, provider error text, request logs never contain X-API-Key/Authorization); pip-audit run
**What I did:** Per-API-key moving-window rate limit middleware (limits library; /health /ready /metrics exempt; error format with request id); upload hardening: magic bytes, size limit with bounded read, filename sanitisation, page-count cap (400); redaction tests (log values, headers, LLM payload log, provider error text, request logs never contain X-API-Key/Authorization); pip-audit run
**Files changed:** specbridge/api/middleware.py specbridge/api/main.py specbridge/ingestion/pipeline.py pyproject.toml uv.lock tests/unit/test_security.py tests/integration/test_api_docs_query.py
**Commands run and outcome:** make lint typecheck test (pass)
**Tests:** unit test_security 7 passed; integration upload hardening test; full suite 303 passed
**Eval results (if any):** n/a
**Problems and how I solved them:** slowapi's middleware silently did nothing: with the installed FastAPI, app.routes no longer exposes included routers' endpoints, so slowapi found no handler and exempted every route. The rate-limit test caught it (all 5 requests returned 200). Replaced by a small middleware on the same 'limits' library and removed the slowapi dependency
**Decisions made:** Rate limit key = X-API-Key (client IP if absent) across all endpoints; pip-audit: 'No known vulnerabilities found' (only our own package skipped, not on PyPI)
**Deviations from spec:** slowapi (spec stack) replaced by its underlying 'limits' library; same behaviour, documented
**Next step:** next task in PROGRESS.md
