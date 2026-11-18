# HTTP API

Base URL `http://localhost:8000` (`make up`). Interactive docs at `/docs` (OpenAPI at `/openapi.json`).
All request and response bodies are Pydantic models. Examples below are real responses from the
running stack with the fake LLM provider (`LLM_PROVIDER=fake`), trimmed for length.

## Conventions

- **Auth:** header `X-API-Key: <key>`; keys come from `API_KEYS=key:user:role,...`. Dev keys (from
  `.env.example`): `dev-viewer-key` (alice), `dev-engineer-key` (bob), `dev-engineer2-key` (erin),
  `dev-approver-key` (carol), `dev-admin-key` (dave). Missing/invalid key -> 401.
- **Roles:**

  | permission | viewer | engineer | approver | admin |
  |---|---|---|---|---|
  | `query`, `read` (documents, extractions, runs, approvals) | yes | yes | yes | yes |
  | `write`: upload documents, run extraction, edit review queue, start/retry agent runs | | yes | yes | yes |
  | `approve`: approve/reject/push extractions, decide change requests (never your own) | | | yes | yes |
  | `admin`: read the audit log | | | | yes |

  Every denial returns 403 and is written to the audit log (`outcome: denied`).
- **Errors:** always `{"error": {"code", "message", "request_id"}}`; the same id is in the
  `X-Request-ID` response header (send your own `X-Request-ID` to propagate it).
  Codes: `unauthorized` 401, `forbidden` 403, `not_found` 404, `conflict` 409, `validation_error` 422,
  `invalid_upload` 400, `invalid_edit` 400, `rate_limited` 429, `budget_exceeded` 503,
  `structured_output_error` 502, `internal_error` 500.
- **Rate limit:** `RATE_LIMIT` (default `60/minute`) per API key; `/health`, `/ready`, `/metrics` exempt.

## Operations

```bash
curl -s localhost:8000/health
# {"status":"ok"}
curl -s localhost:8000/ready
# {"status":"ready","checks":{"database":"ok","embedding_model":"ok","erp":"ok"}}   (503 + details if not)
curl -s localhost:8000/metrics        # Prometheus: requests, LLM calls/tokens/cost, budget, retrieval, extraction, agent
```

## Documents

```bash
# upload (engineer+)
curl -s -X POST localhost:8000/documents -H "X-API-Key: dev-engineer-key" \
  -F "file=@data/corpus/synthetic/kestrel/KD-210_rev1.0.pdf;type=application/pdf"
# -> 201 {"status":"ingested"|"skipped","document":{...},"chunks":3}
# non-PDF / > MAX_UPLOAD_MB / > 400 pages -> 400 {"error":{"code":"invalid_upload",...}}

curl -s -H "X-API-Key: dev-viewer-key" "localhost:8000/documents?latest_only=true"
```
```json
{
 "id": "5d61f710-f423-449e-bc2f-a5f15af472ce",
 "doc_key": "alpenlicht/AL-AIO-201/rev1.0",
 "filename": "AL-AIO-201_rev1.0.pdf",
 "vendor": "Alpenlicht Automation",
 "title": "AlpenIO Analog I/O Module M18",
 "part_numbers": ["AL-AIO-201"],
 "source_type": "synthetic",
 "revision_label": "1.0",
 "is_latest": true,
 "page_count": 1,
 "status": "ingested",
 "error": null
}
```

`GET /documents/{id}` returns one document. `GET /documents/{id}/pages/{page_no}/image?chunk_id=...`
returns a PNG of the page with the chunk's bounding boxes highlighted (cached under
`data/cache/pages/`); without `chunk_id` the plain page.

```bash
curl -s -X POST localhost:8000/documents -H "X-API-Key: dev-viewer-key" -F "file=@x.pdf"
# {"error":{"code":"forbidden","message":"Role 'viewer' lacks permission 'write'","request_id":"..."}}
```

## Query (any role)

`POST /query` `{question (3-1000 chars), index_name?, top_k? (1-30), mode? (vector|keyword|hybrid), rerank?}`

```bash
curl -s -X POST localhost:8000/query -H "X-API-Key: dev-viewer-key" -H "Content-Type: application/json" \
  -d '{"question":"What is the protection class of the KD-210?","top_k":30}'
```
```json
{
 "answer": "Ingress protection | IP 54",
 "citations": [{
   "source_id": "S14", "doc_key": "kestrel/KD-210/rev1.0", "page": 1,
   "quote": "Ingress protection | IP 54",
   "chunk_id": "f56c97f8-9812-43fe-a14c-8bdcc85ad706",
   "document_id": "46435baf-1d9a-4944-b102-551958cdf6d5",
   "image_url": "/documents/46435baf-.../pages/1/image?chunk_id=f56c97f8-..."}],
 "abstained": false, "abstain_reason": null,
 "latency_ms": 55, "cost_usd": 0.0, "request_id": "563b8c2db7d44c3fa5e38a614b939de5"
}
```
(The fake provider answers extractively, hence the table-row answer; a real model writes a sentence.)
When the evidence is insufficient: `"abstained": true`, `abstain_reason` is `low_retrieval_score`,
`model_unanswerable` or `unsupported_answer_blocked`, and `answer` is "I couldn't find support for this
in the documents." (or the model's explanation). Citations are returned only if their quote was
found in the cited chunk.

## Extractions

| call | role | notes |
|---|---|---|
| `POST /extractions` `{document_id, retry?}` | engineer+ | runs extraction -> `validated` or `pending_review` |
| `GET /extractions?status=` / `GET /extractions/{id}` | any | `data` (normalised spec), `evidence` per field `{page, quote}`, `validation_errors` |
| `PATCH /extractions/{id}` `{edits, evidence, mark_reviewed}` | engineer+ | edits are audited (old/new), validation re-runs |
| `POST /extractions/{id}/approve` | approver+ | a `pending_review` item must have been marked reviewed (else 409) |
| `POST /extractions/{id}/reject` `{comment}` | approver+ | |
| `POST /extractions/{id}/push` | approver+ | idempotent; `pushed` or `push_failed` (retry by calling again) |

```bash
curl -s -X PATCH localhost:8000/extractions/$ID -H "X-API-Key: dev-engineer-key" -H "Content-Type: application/json" \
  -d '{"edits":{"weight_g":620},"evidence":{"weight_g":{"page":1,"quote":"Weight [g] 620"}},"mark_reviewed":true}'
```
Statuses: `validated | pending_review | approved | rejected | pushed | push_failed`. Editing an
approved/pushed item -> 409. Unknown field or wrong type -> 400 `invalid_edit`.

## Agent

```bash
curl -s -X POST localhost:8000/agent/runs -H "X-API-Key: dev-engineer-key" -H "Content-Type: application/json" \
  -d '{"request":"Find a replacement for discontinued part KD-240"}'
```
```json
{
 "id": "2e0ad9bd-0466-4a86-b848-c1c00db0ad6a", "requested_by": "bob",
 "state": "AWAITING_APPROVAL",
 "parsed_request": {"part_number": "KD-240", "constraints": []},
 "result": {"change_request": {
    "original_part": "KD-240", "proposed_part": "KD-210",
    "rationale": "KD-210 datasheet states: Supply voltage | 200 to 480 V AC",
    "evidence": [{"chunk_id": "f56c97f8-...", "doc_key": "kestrel/KD-210/rev1.0", "page": 1,
                  "quote": "| Supply voltage | 200 to 480 V AC |"}],
    "requested_by": "bob"}, "...": "original, candidates, ranking"},
 "error": null, "llm_calls_used": 3,
 "approval_id": "5cb452d4-599a-4614-8640-efe2036f72ed", "approval_status": "pending"
}
```

| call | role | notes |
|---|---|---|
| `POST /agent/runs` `{request}` | engineer+ | runs until `AWAITING_APPROVAL` or a terminal state; viewer -> 403 |
| `GET /agent/runs`, `GET /agent/runs/{id}`, `GET /agent/runs/{id}/steps` | any | steps: `step_no, state, tool_name, tool_input, tool_output, status, attempt, latency_ms, error` |
| `POST /agent/runs/{id}/retry` | engineer+ | only for `FAILED` runs with `result.retryable`; resumes from `COMMITTING` |
| `GET /approvals?status=pending` | any | |
| `POST /approvals/{id}/approve` / `reject` `{comment}` | approver+ | **four-eyes:** the requester gets 403 |

```bash
# the requester's colleague approves
curl -s -X POST localhost:8000/approvals/$AID/approve -H "X-API-Key: dev-approver-key" \
  -H "Content-Type: application/json" -d '{"comment":"ok"}'
# -> {"status":"approved","decided_by":"carol", ...}; the run continues to COMMITTING then DONE
curl -s -H "X-API-Key: dev-viewer-key" localhost:8000/agent/runs/$RID/steps
# PARSE_REQUEST, LOOKUP_PART/get_part, SEARCH_CANDIDATES/search_parts, COMPARE/retrieve_evidence x3,
# COMPARE (ranking), DRAFT_CHANGE_REQUEST, AWAITING_APPROVAL, COMMITTING/create_change_request
```

Terminal states: `DONE`, `REJECTED`, `FAILED` (with `error`; `result.retryable` for ERP outages),
`ESCALATED` (no candidates, no evidence-backed ranking, or a limit was hit; `result.escalation_reason`).
A second decision on the same approval -> 409. Approving as the requester:
`{"error":{"code":"forbidden","message":"Four-eyes rule: you cannot decide your own request.",...}}`.

## Audit (admin)

`GET /audit?actor=&action=&outcome=allowed|denied|error&since=<ISO-8601>&limit=` newest first.
Other roles -> 403. Actions include `document.upload`, `extraction.create|edit|reviewed|approve|reject|push`,
`agent.run_started`, `agent.state_transition`, `agent.tool.<name>` (denied tool calls), `approval.requested`,
`approval.decided`, and `<METHOD> <path>` for permission denials.

## UI (server-rendered)

`/ui/login` (paste an API key; sets a signed `HttpOnly; SameSite=Strict` cookie), `/ui/ask`, `/ui/source`,
`/ui/documents`, `/ui/review` (+ `/ui/review/{id}`), `/ui/approvals`, `/ui/runs` (+ `/ui/runs/{id}` timeline).
Same RBAC as the API.
