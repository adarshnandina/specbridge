"""Append-only audit log. There is intentionally no update/delete function."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from specbridge.db.models import AuditLog
from specbridge.logging_setup import get_logger

log = get_logger("specbridge.audit")


def _request_id() -> str | None:
    from structlog.contextvars import get_contextvars

    v = get_contextvars().get("request_id")
    return str(v) if v else None


def record(
    db: Session,
    *,
    actor: str | None,
    role: str | None,
    action: str,
    outcome: str = "allowed",
    resource_type: str | None = None,
    resource_id: Any = None,
    details: dict[str, Any] | None = None,
) -> None:
    db.add(
        AuditLog(
            request_id=_request_id(),
            actor=actor,
            role=role,
            action=action,
            outcome=outcome,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            details=details or {},
        )
    )
    db.flush()
    log.info(
        "audit",
        action=action,
        outcome=outcome,
        actor=actor,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id else None,
    )


def record_denied(
    actor: str | None,
    role: str | None,
    action: str,
    resource_type: str | None = None,
    resource_id: Any = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Record a denial in its OWN transaction so a request rollback cannot lose it."""
    from specbridge.db.session import session_scope

    with session_scope() as s:
        record(
            s,
            actor=actor,
            role=role,
            action=action,
            outcome="denied",
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
        )
