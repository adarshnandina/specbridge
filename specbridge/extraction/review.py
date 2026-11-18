"""Review queue, approval and ERP push for extractions (Section 7.6 steps 5-6)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from specbridge import audit, metrics
from specbridge.auth.api_keys import Principal
from specbridge.db.models import Document, Extraction
from specbridge.erp_client.client import ErpClient, ErpError, idempotency_key
from specbridge.errors import AppError, ConflictError, NotFoundError
from specbridge.extraction.extractor import load_document_pages
from specbridge.extraction.fields import (
    ALL_FIELDS,
    CATEGORIES,
    DIM_FIELD,
    LIST_FIELDS,
    NUMERIC_FIELDS,
)
from specbridge.extraction.schema import SCHEMA_VERSION
from specbridge.extraction.validators import errors, validate
from specbridge.logging_setup import get_logger

log = get_logger("specbridge.extraction")
EDITABLE = ("validated", "pending_review")


def get_or_404(db: Session, extraction_id: uuid.UUID) -> Extraction:
    ex = db.get(Extraction, extraction_id)
    if ex is None:
        raise NotFoundError("Extraction not found")
    return ex


def _coerce(field: str, value: Any) -> Any:
    """Type-check an edited value (canonical units expected)."""
    if value is None:
        return None
    if field in NUMERIC_FIELDS:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise AppError(f"{field} must be a number", code="invalid_edit")
        return value
    if field == DIM_FIELD:
        if not (
            isinstance(value, list)
            and len(value) == 3
            and all(isinstance(x, int | float) and not isinstance(x, bool) for x in value)
        ):
            raise AppError("dimensions_mm must be [w, h, d] numbers", code="invalid_edit")
        return value
    if field in LIST_FIELDS:
        if not (isinstance(value, list) and all(isinstance(x, str) and x.strip() for x in value)):
            raise AppError(f"{field} must be a list of strings", code="invalid_edit")
        return [x.strip() for x in value] or None
    if not isinstance(value, str):
        raise AppError(f"{field} must be a string", code="invalid_edit")
    value = value.strip()
    if field == "category" and value not in CATEGORIES:
        raise AppError(f"category must be one of {CATEGORIES}", code="invalid_edit")
    return value or None


def revalidate(db: Session, ex: Extraction) -> None:
    doc = db.get(Document, ex.document_id)
    assert doc is not None
    pages, _ = load_document_pages(db, doc)
    issues = validate(ex.data, ex.evidence, pages)
    ex.validation_errors = [i.model_dump() for i in issues]
    ex.status = "pending_review" if errors(issues) else "validated"


def edit_extraction(
    db: Session,
    ex: Extraction,
    p: Principal,
    edits: dict[str, Any],
    evidence: dict[str, dict[str, Any]] | None = None,
    mark_reviewed: bool = False,
) -> Extraction:
    if ex.status not in EDITABLE:
        raise ConflictError(f"Extraction in status {ex.status!r} can no longer be edited")
    unknown = [f for f in list(edits) + list(evidence or {}) if f not in ALL_FIELDS]
    if unknown:
        raise AppError(f"Unknown field(s): {unknown}", code="invalid_edit")
    data, ev = dict(ex.data), {k: dict(v) for k, v in ex.evidence.items()}
    for f, new in edits.items():
        new = _coerce(f, new)
        old = data.get(f)
        if old != new:
            audit.record(
                db,
                actor=p.user,
                role=p.role,
                action="extraction.edit",
                resource_type="extraction",
                resource_id=ex.id,
                details={"field": f, "old": old, "new": new},
            )
        data[f] = new
        if new is None:
            ev.pop(f, None)
    for f, e in (evidence or {}).items():
        ev[f] = {"page": e.get("page"), "quote": e.get("quote")}
    ex.data, ex.evidence = data, ev  # reassign so JSONB change is detected
    revalidate(db, ex)
    if mark_reviewed:
        ex.reviewed_by, ex.reviewed_at = p.user, datetime.now(UTC)
        audit.record(
            db,
            actor=p.user,
            role=p.role,
            action="extraction.reviewed",
            resource_type="extraction",
            resource_id=ex.id,
            details={"status": ex.status, "open_errors": len(errors_of(ex))},
        )
    metrics.EXTRACTION_STATUS.labels(ex.status).inc()
    db.flush()
    return ex


def errors_of(ex: Extraction) -> list[dict[str, Any]]:
    return [i for i in ex.validation_errors if i.get("severity") == "error"]


def approve(db: Session, ex: Extraction, p: Principal) -> Extraction:
    if ex.status not in EDITABLE:
        raise ConflictError(f"Cannot approve an extraction in status {ex.status!r}")
    if ex.status == "pending_review" and ex.reviewed_by is None:
        raise ConflictError("Extraction has validation errors and has not been reviewed")
    ex.status, ex.approved_by, ex.approved_at = "approved", p.user, datetime.now(UTC)
    audit.record(
        db,
        actor=p.user,
        role=p.role,
        action="extraction.approve",
        resource_type="extraction",
        resource_id=ex.id,
    )
    metrics.EXTRACTION_STATUS.labels("approved").inc()
    db.flush()
    return ex


def reject(db: Session, ex: Extraction, p: Principal, comment: str = "") -> Extraction:
    if ex.status in ("pushed", "approved"):
        raise ConflictError(f"Cannot reject an extraction in status {ex.status!r}")
    ex.status = "rejected"
    audit.record(
        db,
        actor=p.user,
        role=p.role,
        action="extraction.reject",
        resource_type="extraction",
        resource_id=ex.id,
        details={"comment": comment},
    )
    metrics.EXTRACTION_STATUS.labels("rejected").inc()
    db.flush()
    return ex


def push(db: Session, ex: Extraction, p: Principal, erp: ErpClient) -> Extraction:
    """Push an approved extraction to the ERP. Safe to retry: same idempotency key every time."""
    if ex.status == "pushed":
        return ex  # idempotent no-op
    if ex.status not in ("approved", "push_failed"):
        raise ConflictError("Only approved extractions can be pushed")
    part_number = ex.data.get("part_number")
    if not part_number:
        raise ConflictError("Extraction has no part_number")
    key = idempotency_key(str(ex.id), SCHEMA_VERSION)
    ex.erp_idempotency_key = key
    try:
        resp = erp.put_part(part_number, ex.data, key)
    except ErpError as exc:
        ex.status = "push_failed"
        ex.erp_response = {"error": str(exc), "retryable": exc.retryable, "status": exc.status}
        audit.record(
            db,
            actor=p.user,
            role=p.role,
            action="extraction.push",
            outcome="error",
            resource_type="extraction",
            resource_id=ex.id,
            details=ex.erp_response,
        )
        log.error("extraction.push_failed", extraction_id=str(ex.id), error=str(exc))
        metrics.EXTRACTION_STATUS.labels("push_failed").inc()
        db.flush()
        return ex
    ex.status, ex.erp_response = "pushed", resp
    audit.record(
        db,
        actor=p.user,
        role=p.role,
        action="extraction.push",
        resource_type="extraction",
        resource_id=ex.id,
        details={"erp": resp},
    )
    log.info("extraction.pushed", extraction_id=str(ex.id), part_number=part_number)
    metrics.EXTRACTION_STATUS.labels("pushed").inc()
    db.flush()
    return ex


def list_extractions(db: Session, status: str | None = None) -> list[Extraction]:
    stmt = select(Extraction).order_by(Extraction.created_at.desc())
    if status:
        stmt = stmt.where(Extraction.status == status)
    return list(db.scalars(stmt))
