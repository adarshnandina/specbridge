from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from specbridge import audit
from specbridge.api.deps import get_db, get_erp, require
from specbridge.api.routers.query import get_llm
from specbridge.auth.api_keys import Principal
from specbridge.db.models import Extraction
from specbridge.erp_client.client import ErpClient
from specbridge.extraction import review
from specbridge.extraction.extractor import extract_document
from specbridge.llm.usage import LLMService

router = APIRouter(prefix="/extractions", tags=["extractions"])


class ExtractionOut(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    schema_version: str
    model: str
    prompt_version: str
    status: str
    data: dict[str, Any]
    evidence: dict[str, Any]
    validation_errors: list[Any]
    attempts: int
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    approved_by: str | None = None
    approved_at: datetime | None = None
    erp_idempotency_key: str | None = None
    erp_response: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


class ExtractIn(BaseModel):
    document_id: uuid.UUID
    retry: bool = True


class PatchIn(BaseModel):
    edits: dict[str, Any] = Field(default_factory=dict)
    evidence: dict[str, dict[str, Any]] = Field(default_factory=dict)
    mark_reviewed: bool = False


class RejectIn(BaseModel):
    comment: str = Field(default="", max_length=500)


@router.post("", response_model=ExtractionOut, status_code=201)
def create_extraction(
    body: ExtractIn,
    db: Session = Depends(get_db),
    llm: LLMService = Depends(get_llm),
    p: Principal = Depends(require("write")),
) -> Extraction:
    ex = extract_document(db, llm, body.document_id, retry=body.retry)
    audit.record(
        db,
        actor=p.user,
        role=p.role,
        action="extraction.create",
        resource_type="extraction",
        resource_id=ex.id,
        details={"status": ex.status},
    )
    return ex


@router.get("", response_model=list[ExtractionOut])
def list_extractions(
    status: str | None = None,
    db: Session = Depends(get_db),
    _: Principal = Depends(require("read")),
) -> list[Extraction]:
    return review.list_extractions(db, status)


@router.get("/{extraction_id}", response_model=ExtractionOut)
def get_extraction(
    extraction_id: uuid.UUID, db: Session = Depends(get_db), _: Principal = Depends(require("read"))
) -> Extraction:
    return review.get_or_404(db, extraction_id)


@router.patch("/{extraction_id}", response_model=ExtractionOut)
def patch_extraction(
    extraction_id: uuid.UUID,
    body: PatchIn,
    db: Session = Depends(get_db),
    p: Principal = Depends(require("write")),
) -> Extraction:
    ex = review.get_or_404(db, extraction_id)
    return review.edit_extraction(db, ex, p, body.edits, body.evidence, body.mark_reviewed)


@router.post("/{extraction_id}/approve", response_model=ExtractionOut)
def approve_extraction(
    extraction_id: uuid.UUID,
    db: Session = Depends(get_db),
    p: Principal = Depends(require("approve")),
) -> Extraction:
    return review.approve(db, review.get_or_404(db, extraction_id), p)


@router.post("/{extraction_id}/reject", response_model=ExtractionOut)
def reject_extraction(
    extraction_id: uuid.UUID,
    body: RejectIn | None = None,
    db: Session = Depends(get_db),
    p: Principal = Depends(require("approve")),
) -> Extraction:
    return review.reject(db, review.get_or_404(db, extraction_id), p, body.comment if body else "")


@router.post("/{extraction_id}/push", response_model=ExtractionOut)
def push_extraction(
    extraction_id: uuid.UUID,
    db: Session = Depends(get_db),
    erp: ErpClient = Depends(get_erp),
    p: Principal = Depends(require("approve")),
) -> Extraction:
    return review.push(db, review.get_or_404(db, extraction_id), p, erp)
