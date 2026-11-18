# 0008 - Synchronous SQLAlchemy and FastAPI endpoints

## Context
The workload is dominated by LLM and embedding latency, not by concurrent I/O; the agent needs
`SELECT ... FOR UPDATE` and commit-per-step semantics; psycopg 3 and SQLAlchemy 2 are mature in sync mode.

## Decision
Sync SQLAlchemy sessions and plain `def` FastAPI endpoints (run in the threadpool). One session per
request; the agent runner commits after every state change so a crash leaves a resumable run.

## Consequences
- Simple, testable code; no async/await colouring through the LLM and ERP clients.
- Throughput is bounded by the threadpool and by blocking LLM calls; a long agent run holds a worker.
  A production deployment would move LLM-bound work to a queue (see LIMITATIONS).
