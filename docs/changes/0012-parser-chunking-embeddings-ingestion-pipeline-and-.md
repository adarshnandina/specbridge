# 2.1 Parser, chunking, embeddings, ingestion pipeline and CLI
## Summary
PyMuPDF parser (blocks+bboxes, tables via find_tables with word-spaced cell text, headings, part-number/revision/vendor detection); fixed and layout chunking with context headers kept out of displayed content; embedder wrapper (bge-small, offline hash embedder for tests); idempotent ingestion with per-index chunks, revision linking, failure recording; 'specbridge ingest' CLI
## Why
Part of milestone task 2.1 in SPECBRIDGE_SPEC.md Section 13.
## Changes (files/modules)
specbridge/ingestion/* specbridge/cli.py tests/unit/test_chunking.py tests/integration/test_ingestion.py
## How it was tested (commands + results)
unit 59 passed total (test_chunking.py 9); integration 8 passed (idempotency, extra index, reingest, revision linking, failure isolation, upload validation). Real run: 'specbridge ingest data/corpus' -> 60 files, 0 failed, 264 chunks (58 tables), 33s incl. model load
## Eval impact (baseline run id → new run id, deltas) or "n/a"
n/a
## Risks / follow-ups
none known
## Self-review checklist
- [x] tests added/updated   - [x] types pass   - [x] lint passes
- [x] no secrets            - [x] logs added for new code paths
- [x] docs updated          - [x] error handling covers failure modes
