# Runbook

Symptom -> diagnosis -> fix. Logs are JSON lines in `logs/app.jsonl` (container: `/app/logs/app.jsonl`);
filter with `specbridge logs tail --event '<glob>'`. Every API error carries a `request_id`: search
for it in the logs and in `audit_log.request_id`.

## Quick checks

```bash
curl -s localhost:8000/ready          # database / embedding_model / erp
docker compose ps && docker compose logs --tail=100 api
specbridge logs tail --event 'agent.*' -n 50
```

## Database down (`/ready` -> `database: error`, API errors `internal_error`)

- **Check:** `docker compose ps db`; `docker compose logs db`; disk space (`df -h`); connections.
- **Fix:** restart `docker compose restart db`; if the volume is full, free space (old backups, Docker
  logs) then restart; if corrupted, restore the last `pg_dump` (DEPLOYMENT.md). The API recovers on its own
  (`pool_pre_ping`). Agent runs are persisted per step and can be resumed afterwards.
- **Events/metrics:** `http.request` with status 500, `api.unhandled`; `sb_http_requests_total{status="500"}`.

## ERP failures

- **Symptoms:** extractions in `push_failed`; agent runs `FAILED` with "ERP unavailable ... " and
  `result.retryable=true`; `/ready` `erp: error`.
- **Diagnosis:** `agent.retry`/`extraction.push_failed` events (each retry attempt is logged);
  `curl $ERP_BASE_URL/health`; for the mock, `curl $ERP/_admin/faults` shows injected faults.
- **Fix:** restore the ERP, then retry: `POST /extractions/{id}/push` (idempotent, same key) or
  `POST /agent/runs/{id}/retry` (resumes from COMMITTING; key = run id). A response lost after a
  successful write is safe: the replay returns the stored result and no duplicate is created. Verify
  with `GET /change-requests` on the ERP.

## Daily LLM budget exceeded (503 `budget_exceeded`)

- **Diagnosis:** `budget.exceeded` event; `sb_llm_budget_remaining_usd`; spend by purpose/model:
  `SELECT purpose, model, sum(cost_usd), count(*) FROM llm_calls WHERE ts >= date_trunc('day', now()) GROUP BY 1,2;`
- **Fix:** find the cause (an eval loop? a runaway client? raise `RATE_LIMIT`-related abuse?); if
  legitimate, raise `LLM_DAILY_BUDGET_USD` and restart the api. The budget resets at the next UTC day.
  Agent runs hit by the guard are `FAILED` (not retryable via the ERP path); start a new run.

## Unknown model price (`KeyError: no pricing for model ...`)

A model id missing from `config/pricing.yaml` is refused before any call (fail closed). Add the price
(or an alias for a Bedrock id) after verifying it on the provider's pricing page.

## Stuck runs awaiting approval

- **Diagnosis:** `GET /approvals?status=pending`; `/ui/approvals`; `SELECT id, requested_by, created_at FROM approvals WHERE status='pending';`
- **Fix:** an approver *other than the requester* approves or rejects. If the requester is the only
  approver, another approver/admin must be added (four-eyes cannot be bypassed). Stale requests can be
  rejected. A run in `AWAITING_APPROVAL` with **no** approval row (crash between DRAFT and approval creation)
  is repaired by `specbridge agent resume <run_id>` (creates the row once).

## Runs stuck in the middle (process crashed)

`SELECT id, state, updated_at FROM agent_runs WHERE state NOT IN ('DONE','REJECTED','FAILED','ESCALATED','AWAITING_APPROVAL');`
then `specbridge agent resume <run_id>` (never automatic). `specbridge agent show <run_id>` prints the steps.

## Ingestion failures

- **Symptoms:** documents with `status=failed` (`GET /documents`), `ingest.failed` events, 400 `invalid_upload`.
- **Diagnosis:** `error` on the document; typical causes: not a PDF (magic bytes), encrypted/corrupt PDF,
  > `MAX_UPLOAD_MB`, > 400 pages, scanned PDF with no text (ingests with 0-1 chunks; no OCR).
- **Fix:** repair/convert the PDF and re-upload; for scans run OCR first. `specbridge ingest <dir> --reingest`
  rebuilds chunks. A duplicate sha256 is skipped (`ingest.skipped_duplicate`) and a missing file is restored.

## Poor answers / abstentions

- Check the retrieval first: `query_logs.retrieval` holds the chunk ids and scores; `retrieval.done`
  logs `top_vector_score`. If the right chunk is missing, run `make eval-retrieval` and compare with the baseline.
- `qa.citation_dropped` / `qa.unsupported_answer_blocked` events show answers rejected for unverifiable quotes.
- Scanned or oddly laid-out PDFs parse poorly (LIMITATIONS.md).

## High latency

- **Break it down:** `sb_retrieval_seconds` (should be tens of ms), `llm.call` events (`latency_ms`,
  `cache_hit`), `http.request.latency_ms`. LLM time dominates normally.
- **Causes/fixes:** provider slowness or rate limits (see retries in `llm.call` status); `RERANK_ENABLED=true`
  adds ~800 ms on CPU; first request after start loads the embedding model (`/ready` waits for it);
  CPU starvation on a small VM; large PDFs during ingestion (ingest off-peak).

## Rate limiting (429)

`rate_limited` is per API key (`RATE_LIMIT`). Check for a polling client. State is per process, so it resets on restart.

## Authentication problems

401 = missing/invalid key; 403 = the role lacks the permission (audited as `denied`; see
`GET /audit?outcome=denied` as admin). UI cookie expires after 8 hours.

## Disk filling up

`data/cache/pages` (rebuildable), Docker logs, `logs/` (rotated), `pg_dump` backups, `eval_results/`.
