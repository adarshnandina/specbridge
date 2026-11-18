from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from specbridge.api.middleware import RequestContextMiddleware
from specbridge.api.routers import agent, documents, extractions, health, query, ui
from specbridge.config import get_settings
from specbridge.errors import AppError
from specbridge.logging_setup import get_logger, setup_logging

log = get_logger("specbridge.api")


def _error(request: Request, status: int, code: str, message: str) -> JSONResponse:
    rid = getattr(request.state, "request_id", None)
    return JSONResponse(
        {"error": {"code": code, "message": message, "request_id": rid}},
        status_code=status,
        headers={"X-Request-ID": rid} if rid else None,
    )


def rate_key(request: Request) -> str:
    return request.headers.get("x-api-key") or (request.client.host if request.client else "anon")


def create_app() -> FastAPI:
    setup_logging()
    s = get_settings()
    app = FastAPI(title="SpecBridge", version="0.1.0")
    limiter = Limiter(key_func=rate_key, default_limits=[s.rate_limit])
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(RequestContextMiddleware)

    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError) -> JSONResponse:
        if exc.status_code >= 500:
            log.error("api.error", code=exc.code, message=exc.message)
        return _error(request, exc.status_code, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        return _error(request, 422, "validation_error", str(exc.errors())[:500])

    @app.exception_handler(RateLimitExceeded)
    async def _rate(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        return _error(request, 429, "rate_limited", f"Rate limit exceeded: {exc.detail}")

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        log.exception("api.unhandled", error=str(exc))
        return _error(request, 500, "internal_error", "Internal server error")

    @app.exception_handler(ui.LoginRedirect)
    async def _login_redirect(request: Request, exc: ui.LoginRedirect) -> RedirectResponse:
        return RedirectResponse("/ui/login", status_code=303)

    @app.exception_handler(PermissionError)
    async def _ui_forbidden(request: Request, exc: PermissionError) -> JSONResponse:
        return _error(request, 403, "forbidden", f"Missing permission: {exc}")

    app.mount(
        "/ui/static",
        StaticFiles(directory=str(Path(__file__).resolve().parents[1] / "ui" / "static")),
        name="ui-static",
    )
    app.include_router(ui.router)

    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        return RedirectResponse("/ui/ask", status_code=303)

    app.include_router(health.router)
    app.include_router(documents.router)
    app.include_router(extractions.router)
    app.include_router(agent.router)
    app.include_router(query.router)
    return app


app = create_app()
