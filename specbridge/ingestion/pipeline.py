"""Ingestion pipeline: validate -> store -> parse -> chunk -> embed -> persist (one tx per doc)."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from specbridge.db.models import Chunk, Document, Page
from specbridge.db.session import session_scope
from specbridge.errors import UploadError
from specbridge.ingestion.chunking import ChunkOptions, make_chunks
from specbridge.ingestion.embeddings import Embedder, get_embedder
from specbridge.ingestion.parser import ParsedDocument, parse_pdf
from specbridge.ingestion.storage import (
    relative_path,
    sanitize_filename,
    store_pdf,
    validate_pdf_bytes,
)
from specbridge.logging_setup import get_logger

log = get_logger("specbridge.ingest")
MAX_PAGES = 400  # reject absurdly long PDFs (resource-exhaustion guard)
REAL_MANIFEST = Path(__file__).resolve().parents[2] / "corpus" / "real" / "manifest.yaml"


@dataclass
class IngestResult:
    status: str  # ingested | skipped | failed
    filename: str
    document_id: str | None = None
    doc_key: str | None = None
    pages: int = 0
    chunks: int = 0
    tables: int = 0
    duration_s: float = 0.0
    embed_s: float = 0.0
    error: str | None = None


def real_manifest() -> dict[str, dict[str, Any]]:
    if not REAL_MANIFEST.exists():
        return {}
    docs = yaml.safe_load(REAL_MANIFEST.read_text()).get("documents", [])
    return {d["sha256"]: d for d in docs}


def _slug(vendor: str | None) -> str:
    first = (vendor or "unknown").split()[0].lower()
    return re.sub(r"[^a-z0-9]+", "", first) or "unknown"


def _version(label: str | None) -> tuple[int, ...]:
    if not label:
        return (0,)
    return tuple(int(x) for x in re.findall(r"\d+", label)) or (0,)


def link_revisions(db: Session, doc: Document) -> None:
    """Order documents sharing vendor + primary part number by revision; newest is_latest."""
    if not doc.part_numbers:
        return
    pn = doc.part_numbers[0]
    docs = [
        d
        for d in db.scalars(
            select(Document).where(
                Document.vendor == doc.vendor, Document.part_numbers.contains([pn])
            )
        )
        if d.part_numbers and d.part_numbers[0] == pn and d.status == "ingested"
    ]
    docs.sort(key=lambda d: _version(d.revision_label))
    prev: Document | None = None
    for d in docs:
        d.supersedes_id = prev.id if prev else None
        d.is_latest = False
        prev = d
    if docs:
        docs[-1].is_latest = True
    db.flush()


def _unique_doc_key(db: Session, key: str, sha: str) -> str:
    exists = db.scalar(select(Document.id).where(Document.doc_key == key))
    return key if exists is None else f"{key}+{sha[:8]}"


def _build_chunks(
    db: Session,
    doc: Document,
    parsed: ParsedDocument,
    index: str,
    opts: ChunkOptions,
    embedder: Embedder,
) -> tuple[int, float]:
    drafts = make_chunks(parsed, opts, embedder.token_count, doc.doc_key)
    t0 = time.perf_counter()
    vectors = embedder.embed([d.search_text or d.content for d in drafts])
    embed_s = time.perf_counter() - t0
    for d, v in zip(drafts, vectors, strict=True):
        db.add(
            Chunk(
                document_id=doc.id,
                index_name=index,
                strategy=opts.strategy,
                chunk_index=d.chunk_index,
                chunk_type=d.chunk_type,
                page_no=d.page_no,
                content=d.content,
                search_text=d.search_text,
                embedding=v,
                bboxes=d.bboxes,
                token_count=d.token_count,
                meta=d.metadata,
            )
        )
    return len(drafts), embed_s


def ingest_bytes(
    db: Session,
    data: bytes,
    filename: str,
    *,
    index: str,
    opts: ChunkOptions,
    embedder: Embedder | None = None,
    source_type: str = "upload",
    source_url: str | None = None,
    vendor: str | None = None,
    doc_key: str | None = None,
    reingest: bool = False,
) -> IngestResult:
    t0 = time.perf_counter()
    filename = sanitize_filename(filename)
    sha = validate_pdf_bytes(data)
    embedder = embedder or get_embedder()
    existing = db.scalar(select(Document).where(Document.sha256 == sha))
    if existing is not None:
        store_pdf(data, sha)  # heal a missing file (e.g. data dir moved or a fresh volume)
        n = (
            db.scalar(
                select(func.count())
                .select_from(Chunk)
                .where(Chunk.document_id == existing.id, Chunk.index_name == index)
            )
            or 0
        )
        if n > 0 and not reingest:
            log.info("ingest.skipped_duplicate", filename=filename, sha256=sha[:12], index=index)
            return IngestResult(
                "skipped", filename, str(existing.id), existing.doc_key, existing.page_count, n
            )
        if reingest:
            db.execute(
                delete(Chunk).where(Chunk.document_id == existing.id, Chunk.index_name == index)
            )
        parsed_e = parse_pdf(data)
        count, embed_s = _build_chunks(db, existing, parsed_e, index, opts, embedder)
        tables = parsed_e.tables_found
        existing.status, existing.error = "ingested", None
        db.flush()
        return IngestResult(
            "ingested",
            filename,
            str(existing.id),
            existing.doc_key,
            existing.page_count,
            count,
            tables,
            time.perf_counter() - t0,
            embed_s,
        )
    parsed = parse_pdf(data)
    if len(parsed.pages) > MAX_PAGES:
        raise UploadError(f"PDF has {len(parsed.pages)} pages; the limit is {MAX_PAGES}")
    store_pdf(data, sha)
    manifest = real_manifest().get(sha)
    if manifest:
        source_type, source_url = "real", manifest["url"]
        vendor = vendor or manifest["vendor"]
        doc_key = doc_key or manifest["doc_key"]
    vendor = parsed.vendor or vendor
    pn = parsed.part_numbers[0] if parsed.part_numbers else Path(filename).stem
    key = doc_key or f"{_slug(vendor)}/{pn}/rev{parsed.revision or '0'}"
    doc = Document(
        doc_key=_unique_doc_key(db, key, sha),
        sha256=sha,
        filename=filename,
        storage_path=relative_path(sha),
        vendor=vendor,
        title=parsed.title,
        part_numbers=parsed.part_numbers,
        source_type=source_type,
        source_url=source_url,
        revision_label=parsed.revision,
        page_count=len(parsed.pages),
        status="ingested",
    )
    db.add(doc)
    db.flush()
    for p in parsed.pages:
        db.add(
            Page(document_id=doc.id, page_no=p.page_no, width=p.width, height=p.height, text=p.text)
        )
    n_chunks, embed_s = _build_chunks(db, doc, parsed, index, opts, embedder)
    link_revisions(db, doc)
    res = IngestResult(
        "ingested",
        filename,
        str(doc.id),
        doc.doc_key,
        len(parsed.pages),
        n_chunks,
        parsed.tables_found,
        time.perf_counter() - t0,
        embed_s,
    )
    log.info(
        "ingest.document_done",
        filename=filename,
        doc_key=doc.doc_key,
        pages=res.pages,
        chunks=res.chunks,
        tables=res.tables,
        duration_s=round(res.duration_s, 3),
        embedding_s=round(embed_s, 3),
        index=index,
        strategy=opts.strategy,
    )
    return res


def _record_failure(data: bytes | None, filename: str, error: str) -> None:
    """Persist a failed document row (best effort) so the failure is visible."""
    if not data:
        return
    import hashlib

    sha = hashlib.sha256(data).hexdigest()
    try:
        with session_scope() as s:
            if s.scalar(select(Document.id).where(Document.sha256 == sha)) is None:
                s.add(
                    Document(
                        doc_key=f"failed/{filename}+{sha[:8]}",
                        sha256=sha,
                        filename=filename,
                        storage_path="",
                        source_type="upload",
                        status="failed",
                        error=error[:1000],
                        is_latest=False,
                    )
                )
    except Exception as exc:
        log.error("ingest.failure_record_failed", error=str(exc))


def _infer_source_type(path: Path) -> str:
    if "synthetic" in path.parts:
        return "synthetic"
    return "real" if "real" in path.parts else "upload"


def ingest_path(
    path: Path,
    *,
    index: str,
    opts: ChunkOptions,
    reingest: bool = False,
    embedder: Embedder | None = None,
    source_type: str | None = None,
) -> IngestResult:
    """Ingest one file in its own transaction; never raises (failures are recorded)."""
    data: bytes | None = None
    try:
        data = path.read_bytes()
        with session_scope() as s:
            return ingest_bytes(
                s,
                data,
                path.name,
                index=index,
                opts=opts,
                embedder=embedder,
                reingest=reingest,
                source_type=source_type or _infer_source_type(path),
            )
    except Exception as exc:
        msg = f"{type(exc).__name__}: {exc}"
        log.error("ingest.failed", filename=path.name, error=msg)
        if not isinstance(exc, UploadError):
            _record_failure(data, path.name, msg)
        return IngestResult("failed", path.name, error=msg)


def ingest_directory(
    directory: Path,
    *,
    index: str,
    opts: ChunkOptions,
    reingest: bool = False,
    embedder: Embedder | None = None,
) -> list[IngestResult]:
    files = sorted(directory.rglob("*.pdf"))
    log.info(
        "ingest.started",
        directory=str(directory),
        files=len(files),
        index=index,
        strategy=opts.strategy,
    )
    emb = embedder or get_embedder()
    results = []
    for f in files:
        st = "synthetic" if "synthetic" in f.parts else ("real" if "real" in f.parts else None)
        results.append(
            ingest_path(f, index=index, opts=opts, reingest=reingest, embedder=emb, source_type=st)
        )
    log.info(
        "ingest.finished",
        ingested=sum(r.status == "ingested" for r in results),
        skipped=sum(r.status == "skipped" for r in results),
        failed=sum(r.status == "failed" for r in results),
    )
    return results
