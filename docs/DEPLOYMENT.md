# Deployment (single Linux VM)

> **Documentation only.** Nothing in this repository was deployed, and `docker-compose.prod.yml`
> and `docker/Caddyfile` were never executed. Treat the steps as a reviewed plan, and test them on a
> throw-away VM first. The local stack (`docker compose up`) *was* run and is covered by `make test-e2e`.

## Target

One VM (for example an Azure `Standard_D4s_v5` or AWS `m6i.xlarge`: 4 vCPU, 16 GB RAM, 60+ GB disk)
running Docker Engine with Compose v2. Containers: `db` (Postgres 16 + pgvector), `erp-mock` (or your
real ERP adapter), `api`, and `caddy` (reverse proxy with automatic TLS). The image is 2.67 GB
(CPU PyTorch + embedding model baked in, ADR-0009); budget disk and pull time accordingly.

## Prerequisites

- A DNS A/AAAA record for the site name pointing to the VM; ports 80 and 443 open (Caddy needs both
  for ACME HTTP-01/TLS-ALPN); port 22 restricted to your admin addresses. Do **not** open 5433, 8000, 8100.
- Docker Engine + Compose v2, `git`, and either the repository or a pre-built image.
- Secrets in a root-owned file `.env.prod` (mode `0600`), never committed.

## Configuration (`.env.prod`)

```bash
SITE_ADDRESS=specbridge.example.com
POSTGRES_PASSWORD=<long random>
SESSION_SECRET=<long random>                       # required in prod: the app refuses the dev default
API_KEYS=<key1>:<user1>:viewer,<key2>:<user2>:engineer,<key3>:<user3>:approver,<key4>:<user4>:admin
LLM_PROVIDER=anthropic                             # or bedrock; start with fake to smoke test
ANTHROPIC_API_KEY=<secret>
LLM_DAILY_BUDGET_USD=5.00
RATE_LIMIT=60/minute
MAX_UPLOAD_MB=20
```

Generate keys with `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`. `APP_ENV=prod`,
`LOG_LLM_PAYLOADS=false` and the Caddy upload cap (25 MB) come from `docker-compose.prod.yml`.
Do not keep the dev keys.

## First start

```bash
git clone <your internal mirror> specbridge && cd specbridge
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.prod up -d --build
docker compose ps                                   # db, erp-mock, api healthy
curl -fsS https://$SITE_ADDRESS/ready               # {"status":"ready", ...}
```

The api entrypoint runs `alembic upgrade head` before starting. Ingest documents through
`POST /documents`, or copy a corpus into the `appdata` volume and run
`docker compose exec api specbridge ingest /app/data/corpus --index main`.
Seed the mock ERP once (`erp-mock` does it automatically when its database is empty); in a real
deployment point `ERP_BASE_URL` at the ERP adapter, which must honour the `Idempotency-Key` header.

## TLS

Caddy obtains and renews certificates automatically for `SITE_ADDRESS` (see `docker/Caddyfile`; HSTS
and a 25 MB body limit are set). The certificate store is the `caddy_data` volume - back it up or
accept re-issuance (Let's Encrypt rate limits apply).

## Backups

```bash
# nightly at 02:15, keep 14 days  (crontab -e)
15 2 * * * cd /opt/specbridge && docker compose exec -T db pg_dump -U specbridge -Fc specbridge \
  > /var/backups/specbridge/pg_$(date +\%F).dump && find /var/backups/specbridge -name 'pg_*.dump' -mtime +14 -delete
```

Also back up the volumes `appdata` (uploaded PDFs under `documents/`, page-image cache is
rebuildable) and `erpdata` if you use the mock. Test a restore regularly:
`docker compose exec -T db pg_restore -U specbridge -d specbridge --clean --if-exists < pg_2026-11-18.dump`.
Copy backups off the VM. `llm_calls`, `audit_log` and `query_logs` are in Postgres and are covered.

## Logs and monitoring

- The app writes structured JSON to stdout (collected by Docker) and to `/app/logs/app.jsonl`
  (rotating, 10 MB x 5, in the `applogs` volume). Configure Docker's `json-file` driver with
  `max-size`/`max-file` in `/etc/docker/daemon.json` so stdout does not fill the disk.
- `specbridge logs tail --event 'agent.*'` filters the file (`docker compose exec api specbridge logs tail ...`).
- Scrape `https://$SITE_ADDRESS/metrics` from inside your network (restrict it in Caddy if exposed):
  `sb_http_requests_total`, `sb_http_request_seconds`, `sb_llm_calls_total`, `sb_llm_tokens_total`,
  `sb_llm_cost_usd_total`, `sb_llm_budget_remaining_usd`, `sb_retrieval_seconds`,
  `sb_extraction_status_total`, `sb_agent_runs_total`. Suggested alerts: `/ready` failing, budget
  remaining < 20%, `sb_agent_runs_total{state="FAILED"}` rising, 5xx rate, approvals pending for > 1 day.

## Upgrades and migrations

```bash
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.prod build
pg_dump ... # take a backup first
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.prod up -d
```

The entrypoint applies new Alembic revisions on start. Rollback: restore the previous image tag and, if a
migration must be undone, `docker compose exec api alembic downgrade -1` **before** starting the old
code (or restore the backup). Changing `EMBEDDING_MODEL` changes the vector dimension and requires a
migration plus re-ingestion (`specbridge ingest ... --reingest`).

## Switching to AWS Bedrock

1. In the AWS console enable model access for the Anthropic Claude models you want, in the region you will use.
2. Look up the exact **Bedrock model IDs / inference-profile IDs** in the AWS Bedrock documentation
   (they differ from the Anthropic API IDs and by region) and set `BEDROCK_MODEL_ANSWER`,
   `BEDROCK_MODEL_EXTRACTION`, `BEDROCK_MODEL_AGENT`, `BEDROCK_MODEL_JUDGE`, `AWS_REGION`, `LLM_PROVIDER=bedrock`.
3. **Pricing:** Bedrock has independent regional pricing. Verify it on the AWS pricing page and add
   each Bedrock id to `config/pricing.yaml` under `aliases` (mapping to a priced model) or as its own
   entry under `models`. **A model id without a price is refused before any call is made** (the budget guard
   cannot protect an unpriced model).
4. **IAM:** give the VM's instance role (preferred - no keys in files) a policy allowing
   `bedrock:InvokeModel` on the specific model / inference-profile ARNs you use (and, if your SDK path
   needs it, `bedrock:InvokeModelWithResponseStream`). The application uses the default AWS credential
   chain (`anthropic.AnthropicBedrock`), so `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` are only for
   machines without a role; never commit them.
5. Re-run `specbridge eval run --suite qa --provider bedrock --dry-run` for a cost estimate, then a
   real dev run, before pointing users at it.

## Hardening checklist

- [ ] unique strong `API_KEYS`, `SESSION_SECRET`, `POSTGRES_PASSWORD`; dev keys removed
- [ ] `LOG_LLM_PAYLOADS=false`; `APP_ENV=prod`
- [ ] only 80/443 reachable; Postgres, ERP and the API port not published
- [ ] `LLM_DAILY_BUDGET_USD` set; billing alerts configured with the LLM provider
- [ ] backups copied off-host and a restore rehearsed
- [ ] `docker compose exec api pip-audit` (or CI) clean; base images pinned and refreshed monthly
