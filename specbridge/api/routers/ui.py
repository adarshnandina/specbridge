"""Server-rendered UI (Jinja2). Session cookie holds a signed {user, role}; same RBAC as the API."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from itsdangerous import BadSignature, URLSafeTimedSerializer
from sqlalchemy import select
from sqlalchemy.orm import Session

from specbridge import audit
from specbridge.api.deps import audit_denied, get_erp, get_keystore
from specbridge.api.routers.documents import page_image_bytes
from specbridge.api.routers.query import get_llm
from specbridge.auth.api_keys import Principal
from specbridge.auth.rbac import has_permission
from specbridge.config import get_settings
from specbridge.db.models import Document, Extraction
from specbridge.db.session import get_db
from specbridge.erp_client.client import ErpClient
from specbridge.errors import AppError
from specbridge.extraction import review as rv
from specbridge.extraction.extractor import extract_document
from specbridge.extraction.fields import ALL_FIELDS, DIM_FIELD, LIST_FIELDS, NUMERIC_FIELDS
from specbridge.logging_setup import bind_request, get_logger
from specbridge.qa.service import answer_question

log = get_logger("specbridge.ui")
UI_DIR = Path(__file__).resolve().parents[2] / "ui"
templates = Jinja2Templates(directory=str(UI_DIR / "templates"))
router = APIRouter(prefix="/ui", tags=["ui"], include_in_schema=False)
COOKIE = "sb_session"
MAX_AGE = 8 * 3600


class LoginRedirect(Exception):
    pass


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().session_secret, salt="specbridge-ui")


def ui_user(request: Request) -> Principal:
    raw = request.cookies.get(COOKIE)
    if raw:
        try:
            data = _serializer().loads(raw, max_age=MAX_AGE)
            p = Principal(data["u"], data["r"])
            request.state.principal = p
            bind_request(getattr(request.state, "request_id", "-"), p.user, p.role)
            return p
        except (BadSignature, KeyError):
            pass
    raise LoginRedirect()


def ui_require(permission: str):  # type: ignore[no-untyped-def]
    def dep(request: Request, p: Principal = Depends(ui_user)) -> Principal:
        if not has_permission(p.role, permission):
            audit_denied(
                p, f"UI {request.method} {request.url.path}", details={"permission": permission}
            )
            raise PermissionError(permission)
        return p

    return dep


def render(request: Request, name: str, user: Principal | None, **ctx: Any) -> HTMLResponse:
    return templates.TemplateResponse(request, name, {"user": user, **ctx})


@router.get("/", include_in_schema=False)
def index() -> RedirectResponse:
    return RedirectResponse("/ui/ask", status_code=303)


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request) -> HTMLResponse:
    return render(request, "login.html", None)


@router.post("/login")
def login(request: Request, api_key: str = Form(...)) -> Response:
    p = get_keystore().authenticate(api_key)
    if p is None:
        log.warning("auth.denied", reason="ui_login_failed")
        bad = render(request, "login.html", None, flash="Invalid API key", flash_kind="error")
        bad.status_code = 401
        return bad
    resp = RedirectResponse("/ui/ask", status_code=303)
    resp.set_cookie(
        COOKIE,
        _serializer().dumps({"u": p.user, "r": p.role}),
        max_age=MAX_AGE,
        httponly=True,
        samesite="strict",
        secure=get_settings().app_env == "prod",
    )
    return resp


@router.get("/logout")
def logout() -> RedirectResponse:
    resp = RedirectResponse("/ui/login", status_code=303)
    resp.delete_cookie(COOKIE)
    return resp


@router.get("/ask", response_class=HTMLResponse)
def ask_form(request: Request, p: Principal = Depends(ui_require("query"))) -> HTMLResponse:
    return render(request, "ask.html", p)


@router.post("/ask", response_class=HTMLResponse)
def ask(
    request: Request,
    question: str = Form(..., max_length=1000),
    db: Session = Depends(get_db),
    p: Principal = Depends(ui_require("query")),
) -> HTMLResponse:
    from types import SimpleNamespace

    q = question.strip()
    if len(q) < 3:
        return render(request, "ask.html", p, flash="Please enter a question.", flash_kind="error")
    res = answer_question(db, q, get_llm(), actor=p.user)
    return render(request, "ask.html", p, question=q, result=SimpleNamespace(**res.to_dict()))


@router.get("/documents", response_class=HTMLResponse)
def documents(
    request: Request, db: Session = Depends(get_db), p: Principal = Depends(ui_require("read"))
) -> HTMLResponse:
    docs = list(db.scalars(select(Document).order_by(Document.doc_key)))
    return render(request, "documents.html", p, docs=docs)


@router.get("/source", response_class=HTMLResponse)
def source(
    request: Request,
    document_id: uuid.UUID,
    page: int,
    chunk_id: uuid.UUID,
    quote: str = "",
    doc_key: str = "",
    p: Principal = Depends(ui_require("read")),
) -> HTMLResponse:
    return render(
        request,
        "source.html",
        p,
        document_id=document_id,
        page=page,
        chunk_id=chunk_id,
        quote=quote[:500],
        doc_key=doc_key[:200],
    )


@router.get("/page/{document_id}/{page_no}")
def page(
    document_id: uuid.UUID,
    page_no: int,
    chunk_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    p: Principal = Depends(ui_require("read")),
) -> Response:
    png = page_image_bytes(db, document_id, page_no, chunk_id)
    audit.record(
        db,
        actor=p.user,
        role=p.role,
        action="ui.view_page",
        resource_type="document",
        resource_id=document_id,
        details={"page": page_no},
    )
    return Response(png, media_type="image/png", headers={"Cache-Control": "private, max-age=3600"})


# ------------------------------------------------------------------ review UI


def _display(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, list):
        return ", ".join(str(x) for x in v)
    return str(v)


def _parse(field: str, raw: str) -> Any:
    raw = raw.strip()
    if raw == "":
        return None
    if field in NUMERIC_FIELDS:
        try:
            return float(raw.replace(",", "."))
        except ValueError as exc:
            raise AppError(f"{field}: '{raw}' is not a number", code="invalid_edit") from exc
    if field == DIM_FIELD:
        try:
            return [float(x.replace(",", ".")) for x in raw.replace("x", ",").split(",")]
        except ValueError as exc:
            raise AppError("dimensions: use w, h, d numbers", code="invalid_edit") from exc
    if field in LIST_FIELDS:
        return [x.strip() for x in raw.split(",") if x.strip()]
    return raw


@router.get("/review", response_class=HTMLResponse)
def review_queue(
    request: Request, db: Session = Depends(get_db), p: Principal = Depends(ui_require("read"))
) -> HTMLResponse:
    items = rv.list_extractions(db)
    items.sort(key=lambda e: (e.status != "pending_review", e.created_at))
    docs = list(
        db.scalars(select(Document).where(Document.status == "ingested").order_by(Document.doc_key))
    )
    return render(
        request,
        "review.html",
        p,
        items=items,
        docs=docs,
        docs_by_id={d.id: d.doc_key for d in docs},
    )


@router.post("/review/extract")
def review_extract(
    document_id: uuid.UUID = Form(...),
    db: Session = Depends(get_db),
    p: Principal = Depends(ui_require("write")),
) -> Response:
    ex = extract_document(db, get_llm(), document_id)
    audit.record(
        db,
        actor=p.user,
        role=p.role,
        action="extraction.create",
        resource_type="extraction",
        resource_id=ex.id,
        details={"status": ex.status},
    )
    return RedirectResponse(f"/ui/review/{ex.id}", status_code=303)


def _detail(
    request: Request,
    db: Session,
    ex: Extraction,
    p: Principal,
    flash: str | None = None,
    kind: str = "info",
) -> HTMLResponse:
    doc = db.get(Document, ex.document_id)
    return render(
        request,
        "review_detail.html",
        p,
        ex=ex,
        fields=ALL_FIELDS,
        display=_display,
        doc_key=doc.doc_key if doc else "?",
        flash=flash,
        flash_kind=kind,
        can_write=has_permission(p.role, "write"),
        can_approve=has_permission(p.role, "approve"),
    )


@router.get("/review/{extraction_id}", response_class=HTMLResponse)
def review_detail(
    request: Request,
    extraction_id: uuid.UUID,
    db: Session = Depends(get_db),
    p: Principal = Depends(ui_require("read")),
) -> HTMLResponse:
    return _detail(request, db, rv.get_or_404(db, extraction_id), p)


@router.post("/review/{extraction_id}/edit", response_class=HTMLResponse)
async def review_edit(
    request: Request,
    extraction_id: uuid.UUID,
    db: Session = Depends(get_db),
    p: Principal = Depends(ui_require("write")),
) -> HTMLResponse:
    form = await request.form()
    ex = rv.get_or_404(db, extraction_id)
    edits: dict[str, Any] = {}
    evidence: dict[str, dict[str, Any]] = {}
    try:
        for f in ALL_FIELDS:
            if f"v__{f}" not in form:
                continue  # only fields actually submitted are edited
            new = _parse(f, str(form.get(f"v__{f}", "")))
            if new != ex.data.get(f):
                edits[f] = new
            q, pg = str(form.get(f"q__{f}", "")).strip(), str(form.get(f"p__{f}", "")).strip()
            old = ex.evidence.get(f) or {}
            if (q or pg) and (q != (old.get("quote") or "") or pg != str(old.get("page") or "")):
                evidence[f] = {"quote": q or None, "page": int(pg) if pg.isdigit() else None}
        ex = rv.edit_extraction(db, ex, p, edits, evidence, bool(form.get("mark_reviewed")))
    except AppError as exc:
        return _detail(request, db, ex, p, exc.message, "error")
    return _detail(request, db, ex, p, "Saved. Validation re-run.", "success")


@router.post("/review/{extraction_id}/approve")
def review_approve(
    request: Request,
    extraction_id: uuid.UUID,
    db: Session = Depends(get_db),
    p: Principal = Depends(ui_require("approve")),
) -> Response:
    rv.approve(db, rv.get_or_404(db, extraction_id), p)
    return RedirectResponse(f"/ui/review/{extraction_id}", status_code=303)


@router.post("/review/{extraction_id}/reject")
def review_reject(
    extraction_id: uuid.UUID,
    db: Session = Depends(get_db),
    p: Principal = Depends(ui_require("approve")),
) -> Response:
    rv.reject(db, rv.get_or_404(db, extraction_id), p, "rejected in UI")
    return RedirectResponse(f"/ui/review/{extraction_id}", status_code=303)


@router.post("/review/{extraction_id}/push")
def review_push(
    extraction_id: uuid.UUID,
    db: Session = Depends(get_db),
    erp: ErpClient = Depends(get_erp),
    p: Principal = Depends(ui_require("approve")),
) -> Response:
    rv.push(db, rv.get_or_404(db, extraction_id), p, erp)
    return RedirectResponse(f"/ui/review/{extraction_id}", status_code=303)
