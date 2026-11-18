from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache

from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session

from specbridge import audit
from specbridge.auth.api_keys import KeyStore, Principal
from specbridge.auth.rbac import has_permission
from specbridge.config import get_settings
from specbridge.db.session import get_db
from specbridge.erp_client.client import ErpClient
from specbridge.errors import AuthError, ForbiddenError
from specbridge.logging_setup import bind_request, get_logger

log = get_logger("specbridge.auth")


@lru_cache
def get_keystore() -> KeyStore:
    return KeyStore(get_settings().parsed_api_keys())


def authenticate(request: Request, x_api_key: str | None = Header(default=None)) -> Principal:
    p = get_keystore().authenticate(x_api_key)
    if p is None:
        log.warning("auth.denied", reason="missing_or_invalid_key", path=request.url.path)
        raise AuthError("Missing or invalid API key")
    request.state.principal = p
    bind_request(getattr(request.state, "request_id", "-"), p.user, p.role)
    return p


def audit_denied(
    p: Principal,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    details: dict[str, object] | None = None,
) -> None:
    audit.record_denied(p.user, p.role, action, resource_type, resource_id, dict(details or {}))
    log.warning("auth.denied", actor=p.user, role=p.role, action=action)


def require(permission: str) -> Callable[..., Principal]:
    def dep(request: Request, p: Principal = Depends(authenticate)) -> Principal:
        if not has_permission(p.role, permission):
            audit_denied(
                p, f"{request.method} {request.url.path}", details={"permission": permission}
            )
            raise ForbiddenError(f"Role {p.role!r} lacks permission {permission!r}")
        return p

    return dep


_erp: ErpClient | None = None


def get_erp() -> ErpClient:
    global _erp
    if _erp is None:
        _erp = ErpClient()
    return _erp


def set_erp(client: ErpClient | None) -> None:
    global _erp
    _erp = client


__all__ = ["get_erp", "set_erp", "Session", "get_db", "require", "authenticate", "audit_denied"]
