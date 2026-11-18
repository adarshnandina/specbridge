from __future__ import annotations

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

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
