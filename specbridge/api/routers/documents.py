from __future__ import annotations

import uuid
from typing import Any

import pymupdf
from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from specbridge import audit
from specbridge.api.deps import get_db, require
from specbridge.auth.api_keys import Principal
from specbridge.config import get_settings
from specbridge.db.models import Chunk, Document
from specbridge.errors import NotFoundError, UploadError
from specbridge.ingestion.chunking import ChunkOptions
from specbridge.ingestion.pipeline import ingest_bytes
from specbridge.ingestion.storage import validate_pdf_bytes

router = APIRouter(tags=["documents"])


class DocumentOut(BaseModel):
    id: uuid.UUID
    doc_key: str
    filename: str
    vendor: str | None
    title: str | None
    part_numbers: list[str]
    source_type: str
    revision_label: str | None
    is_latest: bool
    page_count: int
    status: str
    error: str | None = None

    model_config = {"from_attributes": True}


class UploadOut(BaseModel):
    status: str
    document: DocumentOut | None = None
    chunks: int = 0


@router.post("/documents", response_model=UploadOut, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    p: Principal = Depends(require("write")),
) -> UploadOut:
    max_bytes = get_settings().max_upload_mb * 1024 * 1024
    data = await file.read(max_bytes + 1)  # never buffer more than limit + 1 byte
    validate_pdf_bytes(data)
    s = get_settings()
    res = ingest_bytes(
        db,
        data,
        file.filename or "upload.pdf",
        index=s.default_index,
        opts=ChunkOptions(s.chunk_strategy),
        source_type="upload",
    )
    doc = db.get(Document, uuid.UUID(res.document_id)) if res.document_id else None
    audit.record(
        db,
        actor=p.user,
        role=p.role,
        action="document.upload",
        resource_type="document",
        resource_id=res.document_id,
        details={"status": res.status, "chunks": res.chunks},
    )
    return UploadOut(
        status=res.status,
        document=DocumentOut.model_validate(doc) if doc else None,
        chunks=res.chunks,
    )


@router.get("/documents", response_model=list[DocumentOut])
def list_documents(
    latest_only: bool = False,
    vendor: str | None = None,
    db: Session = Depends(get_db),
    _: Principal = Depends(require("read")),
) -> list[Document]:
    stmt = select(Document).order_by(Document.doc_key)
    if latest_only:
        stmt = stmt.where(Document.is_latest.is_(True))
    if vendor:
        stmt = stmt.where(Document.vendor == vendor)
    return list(db.scalars(stmt))


@router.get("/documents/{document_id}", response_model=DocumentOut)
def get_document(
    document_id: uuid.UUID, db: Session = Depends(get_db), _: Principal = Depends(require("read"))
) -> Document:
    doc = db.get(Document, document_id)
    if not doc:
        raise NotFoundError("Document not found")
    return doc


def render_page_png(
    pdf_path: str, page_no: int, bboxes: list[list[float]], zoom: float = 1.6
) -> bytes:
    opener: Any = pymupdf.open
    rect_cls: Any = pymupdf.Rect
    matrix_cls: Any = pymupdf.Matrix
    doc = opener(pdf_path)
    try:
        if page_no < 1 or page_no > doc.page_count:
            raise NotFoundError("Page not found")
        page = doc[page_no - 1]
        for bb in bboxes:
            rect = rect_cls(*bb)
            page.draw_rect(
                rect, color=(1, 0.55, 0), fill=(1, 0.85, 0), fill_opacity=0.35, width=1.2
            )
        pix = page.get_pixmap(matrix=matrix_cls(zoom, zoom))
        return bytes(pix.tobytes("png"))
    finally:
        doc.close()


def page_image_bytes(
    db: Session, document_id: uuid.UUID, page_no: int, chunk_id: uuid.UUID | None
) -> bytes:
    """PNG of a page, cited chunk highlighted; cached on disk."""
    doc = db.get(Document, document_id)
    if not doc or doc.status != "ingested":
        raise NotFoundError("Document not found")
    bboxes: list[list[float]] = []
    if chunk_id:
        ch = db.get(Chunk, chunk_id)
        if not ch or ch.document_id != doc.id:
            raise NotFoundError("Chunk not found for this document")
        if ch.page_no == page_no:
            bboxes = ch.bboxes
    cache_dir = get_settings().data_dir / "cache" / "pages"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"{doc.sha256}_{page_no}_{str(chunk_id) if chunk_id else 'plain'}.png"
    if cache_file.exists():
        return cache_file.read_bytes()
    try:
        png = render_page_png(doc.storage_path, page_no, bboxes)
    except NotFoundError:
        raise
    except Exception as exc:
        raise UploadError(f"Could not render page: {exc}") from exc
    cache_file.write_bytes(png)
    return png


@router.get("/documents/{document_id}/pages/{page_no}/image")
def page_image(
    document_id: uuid.UUID,
    page_no: int,
    chunk_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    _: Principal = Depends(require("read")),
) -> Response:
    png = page_image_bytes(db, document_id, page_no, chunk_id)
    return Response(png, media_type="image/png", headers={"Cache-Control": "private, max-age=3600"})
