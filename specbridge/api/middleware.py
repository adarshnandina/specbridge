from __future__ import annotations

import time
import uuid

from limits import parse
from limits.storage import MemoryStorage
from limits.strategies import MovingWindowRateLimiter
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from specbridge import metrics
from specbridge.logging_setup import bind_request, clear_request, get_logger

log = get_logger("specbridge.http")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex
        request.state.request_id = rid
        clear_request()
        bind_request(rid)
        t0 = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["X-Request-ID"] = rid
            return response
        finally:
            dt = time.perf_counter() - t0
            route = request.scope.get("route")
            path_tpl = getattr(route, "path", request.url.path)
            p = getattr(request.state, "principal", None)
            metrics.HTTP_REQUESTS.labels(request.method, path_tpl, str(status)).inc()
            metrics.HTTP_LATENCY.labels(path_tpl).observe(dt)
            log.info(
                "http.request",
                method=request.method,
                path=request.url.path,
                status=status,
                latency_ms=int(dt * 1000),
                actor=getattr(p, "user", None),
                role=getattr(p, "role", None),
            )
            clear_request()


RATE_EXEMPT_PREFIXES = ("/health", "/ready", "/metrics", "/ui/static")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-API-key rate limit (moving window) across all endpoints; falls back to client IP.

    Built directly on the `limits` library: slowapi's middleware cannot see routes registered via
    include_router with current FastAPI versions and then silently exempts every route (found by
    tests/unit/test_security.py::test_rate_limit_is_per_api_key).
    """

    def __init__(self, app: object, limit: str) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self.item = parse(limit)
        self.strategy = MovingWindowRateLimiter(MemoryStorage())

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path.startswith(RATE_EXEMPT_PREFIXES):
            return await call_next(request)
        key = request.headers.get("x-api-key") or (
            request.client.host if request.client else "anon"
        )
        # Only a hash-free, opaque bucket id is used; the key itself is never logged.
        if not self.strategy.hit(self.item, "rl", key):
            rid = getattr(request.state, "request_id", None)
            log.warning("http.rate_limited", path=request.url.path)
            return JSONResponse(
                {
                    "error": {
                        "code": "rate_limited",
                        "request_id": rid,
                        "message": f"Rate limit exceeded: {self.item}",
                    }
                },
                status_code=429,
                headers={"Retry-After": "60", **({"X-Request-ID": rid} if rid else {})},
            )
        return await call_next(request)
