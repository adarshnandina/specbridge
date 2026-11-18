from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from specbridge.api.deps import get_db, require
from specbridge.auth.api_keys import Principal
from specbridge.db.models import AuditLog

router = APIRouter(tags=["audit"])


class AuditOut(BaseModel):
    id: uuid.UUID
    ts: datetime
    request_id: str | None
    actor: str | None
    role: str | None
    action: str
    resource_type: str | None
    resource_id: str | None
    outcome: str
    details: dict[str, Any]

    model_config = {"from_attributes": True}


@router.get("/audit", response_model=list[AuditOut])
def read_audit(
    actor: str | None = None,
    action: str | None = Query(default=None, description="exact action name"),
    outcome: str | None = Query(default=None, pattern="^(allowed|denied|error)$"),
    since: datetime | None = Query(default=None, description="ISO-8601 timestamp"),
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
    _: Principal = Depends(require("admin")),
) -> list[AuditLog]:
    """Append-only audit trail (admin only). Whitelisted filters; newest first."""
    stmt = select(AuditLog).order_by(AuditLog.ts.desc()).limit(limit)
    if actor:
        stmt = stmt.where(AuditLog.actor == actor)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if outcome:
        stmt = stmt.where(AuditLog.outcome == outcome)
    if since:
        stmt = stmt.where(AuditLog.ts >= since)
    return list(db.scalars(stmt))
