# SpecBridge — rules for Claude Code

Full specification: SPECBRIDGE_SPEC.md

## Hard rules (never violate)
1. **No GitHub.** Never add a git remote, never `git push`, never run the `gh` CLI, never call the GitHub API, never create repositories, pull requests, issues, gists or releases. A **local** git repository with **local** commits is allowed and required (it is the project history). The CI workflow file (Section 11.3) is written but never triggered from here.
2. **No secrets in files that are committed.** `.env` is git-ignored. Only `.env.example` with placeholders is committed. Never print API keys into logs, the journal or commit messages.
3. **Stay inside the project directory.** Do not modify files outside it. No global package installs (use `uv` virtual environments). Do not change system settings.
4. **Never fabricate results.** Every metric, latency, cost or percentage written in any document must come from an actual run recorded in `eval_results/` and must reference its run id. If a run could not be executed, write "not yet run" and the reason.
5. **Never deploy.** Write deployment files and docs, but do not deploy to any cloud or VM.
6. **Spend limit.** Never let a single eval run exceed `EVAL_MAX_COST_USD` (default 2.00 USD) or the daily LLM budget `LLM_DAILY_BUDGET_USD` (default 5.00 USD). Estimate cost before paid runs; use the response cache when re-running.
7. **Ground truth honesty.** Labels you (Claude) create for real-world documents are marked `"verified_by_human": false`, and metrics on them are reported as *provisional*.

## Session start routine
1. Read `CLAUDE.md`, `docs/build-log/PROGRESS.md`, and the last 3 entries of `docs/build-log/JOURNAL.md`.
2. Continue with the first unchecked task in `PROGRESS.md`.

## Task loop (every task)
1. Mark the task `in progress` in `PROGRESS.md`.
2. Implement in small steps, writing tests alongside.
3. Run checks (`make lint typecheck test`; `make test-int` when DB code changed).
4. Write a change note in `docs/changes/NNNN-<slug>.md`.
5. Append a journal entry to `docs/build-log/JOURNAL.md`.
6. Mark the task `done` in `PROGRESS.md`.
7. Commit locally: `git add -A && git commit -m "<milestone>.<task>: <summary>"`. Never push.

## Stop and ask only when
- A prerequisite is missing (Python 3.12, uv, Docker running).
- An API key is needed for a paid run: do NOT stop; finish fake-provider work, mark `blocked: needs API key`, list under "Needs user", ask once at the end.
- An action would fall outside the hard rules.

## Key make commands
`make setup | fmt | lint | typecheck | test | test-int | test-e2e | audit | ci | up | down | migrate | corpus | ingest | eval-retrieval | eval-all | gate-retrieval | experiments`
