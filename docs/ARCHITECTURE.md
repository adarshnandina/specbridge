# Architecture

SpecBridge is one FastAPI service (`specbridge/`), one PostgreSQL+pgvector database, and a separate
mock ERP service (`erp_mock/`). All LLM access goes through one provider layer.

```mermaid
flowchart LR
    U[Engineer / approver<br/>browser or curl] -->|X-API-Key or UI cookie| API[FastAPI<br/>specbridge.api]
    API --> ING[ingestion<br/>parser, chunking, embeddings]
    API --> RET[retrieval<br/>vector, keyword, RRF, rerank]
    API --> QA[qa<br/>citations, abstention]
    API --> EXT[extraction<br/>normalise, validate, review]
    API --> AG[agent<br/>state machine]
    QA --> LLM[LLMService<br/>budget, cache, usage]
    EXT --> LLM
    AG --> LLM
    LLM --> P{provider}
    P --> A[Anthropic]
    P --> B[Bedrock]
    P --> F[Fake - tests/CI]
    ING --> DB[(PostgreSQL + pgvector)]
    RET --> DB
    QA --> DB
    EXT --> DB
    AG --> DB
    EXT -->|PUT /parts, Idempotency-Key| ERP[erp-mock<br/>SQLite]
    AG -->|POST /change-requests, Idempotency-Key| ERP
    EVAL[eval runner<br/>specbridge eval ...] --> RET
    EVAL --> QA
    EVAL --> EXT
    EVAL --> AG
```

## Modules

| module | responsibility |
|---|---|
| `config.py`, `logging_setup.py`, `metrics.py`, `errors.py` | pydantic-settings (fail fast), structlog JSON logging with redaction, Prometheus metrics, error types mapped to `{"error": {code, message, request_id}}` |
| `db/` | SQLAlchemy models (Section 6 of the spec), sessions, Alembic migration `0001`, ephemeral databases for hermetic evals |
| `llm/` | provider protocol, Anthropic/Bedrock/Fake providers, pricing from `config/pricing.yaml`, budget guard, response cache, usage accounting, forced-tool structured output |
| `ingestion/` | PDF validation, PyMuPDF parser (blocks, tables, headings), `fixed` and `layout` chunking, embeddings, idempotent pipeline, revision linking |
| `retrieval/` | `vector` (default), `keyword`, `hybrid` (RRF k=60, tie-aware ranks), optional cross-encoder rerank; deterministic tie-breaks |
| `qa/` | prompt, untrusted-source wrapping, citation verification, abstention |
| `extraction/` | schema, units, normalisation, validators, extractor with retry, review/approve/push, eval suite |
| `erp_client/` | httpx client with retries and idempotency keys |
| `agent/` | states, permissions, tools, runner, scenario engine, eval suite |
| `auth/`, `audit.py` | API keys, RBAC matrix, append-only audit log |
| `api/` | routers (`health`, `documents`, `query`, `extractions`, `agent`, `audit`, `ui`), middleware (request id, rate limit), dependencies |
| `eval/` | datasets, metrics, stats, runner, compare, gate, judge, calibration, experiments |

## Data model

```mermaid
erDiagram
    documents ||--o{ pages : has
    documents ||--o{ chunks : has
    documents ||--o{ extractions : "extracted from"
    documents |o--o| documents : supersedes
    agent_runs ||--o{ agent_steps : has
    agent_runs ||--o| approvals : "awaits"
    documents { uuid id string doc_key string sha256 bool is_latest string revision_label uuid supersedes_id }
    chunks { uuid id string index_name string strategy string chunk_type int page_no text content text search_text vector embedding jsonb bboxes jsonb metadata }
    extractions { uuid id string status jsonb data jsonb evidence jsonb validation_errors string erp_idempotency_key }
    agent_runs { uuid id string state jsonb parsed_request jsonb result int llm_calls_used }
    approvals { uuid id string status string requested_by string decided_by jsonb change_request }
    audit_log { uuid id string actor string action string outcome jsonb details }
    llm_calls { uuid id string purpose string model int input_tokens float cost_usd bool cache_hit }
    query_logs { uuid id string question jsonb retrieval bool abstained }
```

Notes: `chunks.search_text` (context header + content) feeds the embedding and a generated
`content_tsv` (`simple` config); `chunks.content` stays clean for citations. `chunks.index_name`
lets several chunkings coexist. `storage_path` is relative to `DATA_DIR`.

## Data flows

### Ingestion

```mermaid
sequenceDiagram
    participant C as Client / CLI
    participant P as pipeline
    participant S as storage
    participant D as parser+chunker
    participant E as embedder
    participant DB as Postgres
    C->>P: PDF bytes
    P->>P: magic bytes, size, sha256, filename sanitised
    alt sha256 known and index already has chunks
        P-->>C: skipped (ingest.skipped_duplicate)
    else new document (or new index)
        P->>S: store documents/<sha>.pdf
        P->>D: parse: blocks+bboxes, tables, headings, part numbers, revision
        D->>D: chunk (layout: headings, tables as own chunks, context header)
        P->>E: embed(header + content) in batches
        P->>DB: one transaction: document, pages, chunks
        P->>DB: link revisions (newest is_latest, supersedes_id)
    end
```

A failure marks the document `failed` and the directory run continues with the next file.

### Question answering

```mermaid
sequenceDiagram
    participant C as Client
    participant Q as qa.service
    participant R as retrieval
    participant L as LLMService
    participant DB as Postgres
    C->>Q: question
    Q->>R: retrieve(mode, top_k, rerank)
    R->>DB: vector top-k (default) | keyword | hybrid: vector + FTS top 30 -> RRF (tie-aware)
    alt no chunks or best similarity < ABSTAIN_MIN_SCORE
        Q-->>C: abstain (no LLM call)
    else
        Q->>L: system rules + <source id doc page> chunks (untrusted) + question
        L-->>Q: submit_answer {answerable, answer, citations[quote]}
        Q->>Q: each quote must fuzzy-match its source (>= 90)
        alt answerable but no valid citation
            Q-->>C: abstain (qa.unsupported_answer_blocked)
        else
            Q->>DB: query_logs row
            Q-->>C: answer + citations (+ highlighted page image URLs)
        end
    end
```

### Extraction, review and push

```mermaid
stateDiagram-v2
    [*] --> validated: extract, all checks pass
    [*] --> pending_review: errors after one retry
    pending_review --> validated: engineer edits, revalidation passes
    validated --> approved: approver
    pending_review --> approved: only after a human marked it reviewed
    validated --> rejected
    pending_review --> rejected
    approved --> pushed: ERP PUT (key = sha256(extraction_id + schema_version))
    approved --> push_failed: ERP unavailable after retries
    push_failed --> pushed: retry (same key, no duplicate)
```

The LLM (`submit_spec` forced tool) returns `{value, unit, page, quote}` per field. Normalisation and
validation are deterministic (ADR-0005); there is no confidence score anywhere.

### Part-substitution agent

```mermaid
stateDiagram-v2
    [*] --> RECEIVED
    RECEIVED --> PARSE_REQUEST
    PARSE_REQUEST --> LOOKUP_PART: LLM parse, whitelisted fields
    LOOKUP_PART --> SEARCH_CANDIDATES: tool get_part (ERP)
    SEARCH_CANDIDATES --> COMPARE: tool search_parts (deterministic SQL)
    COMPARE --> DRAFT_CHANGE_REQUEST: LLM + retrieve_evidence (max 3), cited
    DRAFT_CHANGE_REQUEST --> AWAITING_APPROVAL: creates approvals row (pending)
    AWAITING_APPROVAL --> COMMITTING: approved by a DIFFERENT user
    AWAITING_APPROVAL --> REJECTED: rejected
    COMMITTING --> DONE: tool create_change_request (key = run id)
    COMMITTING --> FAILED: ERP down after 3 attempts (retryable)
    FAILED --> COMMITTING: POST /agent/runs/{id}/retry
    PARSE_REQUEST --> FAILED: invalid request / invalid structured output twice
    LOOKUP_PART --> FAILED: part not found
    SEARCH_CANDIDATES --> ESCALATED: no candidates
    COMPARE --> ESCALATED: no evidence-backed ranking, LLM-call or time limit
    DONE --> [*]
    REJECTED --> [*]
    ESCALATED --> [*]
```

```mermaid
sequenceDiagram
    participant E as engineer (requester)
    participant A as API + AgentRunner
    participant DB as Postgres
    participant AP as approver (different user)
    participant ERP as ERP
    E->>A: POST /agent/runs
    A->>DB: run, steps, audit per transition (commit each)
    A-->>E: state AWAITING_APPROVAL, approval pending
    Note over A,ERP: nothing has been written to the ERP
    AP->>A: POST /approvals/{id}/approve
    A->>A: four-eyes: approver != requester, else 403 + audit denied
    A->>DB: approval approved, state COMMITTING
    A->>A: write tool requires an approved approval row for THIS run
    A->>ERP: POST /change-requests (Idempotency-Key = run id, 3 attempts)
    ERP-->>A: 201 (or replay of the stored response)
    A->>DB: DONE
```

## Security design

- **Prompt injection.** Document text is data: wrapped as `<source>`, `<page>`, `<candidates>` tags with
  closing-tag escaping, system rules say never to obey it, answers need verified citations, and the
  agent's safety is code, not prompt: per-state tool allowlists (the write tool exists only in
  `COMMITTING`), a write guard that queries for an approved approval row, a four-eyes rule, and
  document text can never cause a state transition. The corpus contains an injection datasheet
  (`AL-DIO-199`); scenarios S10 and S12 script a model that obeys it and show the write is denied and
  nothing is sent to the ERP.
- **No LLM-generated SQL.** `search_parts` builds a parameterised SQLAlchemy query from whitelisted,
  Pydantic-validated constraint fields. Query filters on the API are whitelisted.
- **AuthN/Z.** `X-API-Key` compared with `hmac.compare_digest`; RBAC matrix (viewer, engineer,
  approver, admin) enforced by a dependency; every denial is audited in its own transaction so a
  request rollback cannot lose it. The `audit_log` has no update or delete code path.
- **Input validation.** PDF magic bytes, size limit with a bounded read, page-count cap, filename
  sanitisation, Pydantic bodies, `SameSite=Strict` HttpOnly session cookie for the UI, HTML autoescape.
- **Abuse and cost.** Per-key rate limit; daily LLM budget guard returns 503 `budget_exceeded`;
  eval runs abort above `EVAL_MAX_COST_USD`.
- **Secrets.** Environment only; `.env` is git-ignored; log values and the `X-API-Key`/`Authorization`
  headers are redacted; LLM payload logging is off in the prod compose file.
- **Containers** run as a non-root user on a slim base; `pip-audit` runs in `make ci`.

## Failure modes and how each is handled

| failure | handling |
|---|---|
| Database down | `/ready` 503 (`database: error`); requests fail with 500 `internal_error` and a request id; Docker healthcheck stays on `/health` |
| Embedding model missing | `/ready` 503 (`embedding_model: error`) |
| LLM rate limit / 5xx / timeout | tenacity exponential backoff with jitter (`LLM_MAX_RETRIES`); 4xx are not retried; every attempt is accounted |
| LLM invalid structured output | one retry with the validation error appended, then `StructuredOutputError` -> 502 (QA/extraction) or agent `FAILED` with a clear message |
| Daily budget exceeded | `BudgetExceededError` -> 503 `budget_exceeded`; `budget.exceeded` logged; agent run `FAILED` |
| Unsupported / fabricated answer | invalid citations dropped and logged; answer blocked and replaced by an abstention |
| Extraction fails validation | one retry with errors; else `pending_review` for a human |
| ERP transient failure | 3 attempts with backoff, same idempotency key; lost responses replay the stored result |
| ERP down | extraction push -> `push_failed` (retryable); agent run `FAILED` with `retryable=true`, `POST /agent/runs/{id}/retry` |
| Process crash mid-run | each transition is committed; `specbridge agent resume <run_id>` (explicit, never automatic) |
| Duplicate approval click | second decision -> 409; the approval row is locked `FOR UPDATE` |
| Malformed / hostile upload | rejected before parsing (400); a failing parse records a `failed` document and the batch continues |
| Ingestion of a moved data dir | paths are relative to `DATA_DIR`; duplicate uploads re-store a missing file |
| Rate limit exceeded | 429 `rate_limited` with `Retry-After` |
