from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text

from specbridge.config import get_settings
from specbridge.db.session import get_engine
from specbridge.ingestion import embeddings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def ready() -> JSONResponse:
    checks: dict[str, Any] = {}
    try:
        with get_engine().connect() as c:
            c.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {type(exc).__name__}"
    try:
        embeddings.get_embedder()
        checks["embedding_model"] = "ok"
    except Exception as exc:
        checks["embedding_model"] = f"error: {type(exc).__name__}: {exc}"[:200]
    try:
        r = httpx.get(f"{get_settings().erp_base_url}/health", timeout=2.0)
        checks["erp"] = "ok" if r.status_code == 200 else f"error: status {r.status_code}"
    except Exception as exc:
        checks["erp"] = f"error: {type(exc).__name__}"
    ok = all(v == "ok" for v in checks.values())
    return JSONResponse(
        {"status": "ready" if ok else "not_ready", "checks": checks}, status_code=200 if ok else 503
    )


@router.get("/metrics")
def metrics_endpoint() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
