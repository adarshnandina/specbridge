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
from specbridge.api.deps import audit_denied, get_keystore
from specbridge.api.routers.documents import page_image_bytes
from specbridge.api.routers.query import get_llm
from specbridge.auth.api_keys import Principal
from specbridge.auth.rbac import has_permission
from specbridge.config import get_settings
from specbridge.db.models import Document
from specbridge.db.session import get_db
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
