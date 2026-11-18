"""HTTP client for the (mock) ERP with retries on 5xx/timeouts and mandatory idempotency keys."""

from __future__ import annotations

import hashlib
from typing import Any

import httpx
from tenacity import (
    RetryError,
    Retrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

from specbridge.config import get_settings
from specbridge.logging_setup import get_logger

log = get_logger("specbridge.erp")


class ErpError(Exception):
    def __init__(self, message: str, status: int | None = None, retryable: bool = False) -> None:
        super().__init__(message)
        self.status = status
        self.retryable = retryable


class _Transient(ErpError):
    pass


def idempotency_key(*parts: str) -> str:
    """Stable key: sha256 of the joined parts (e.g. extraction_id + schema_version)."""
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def _is_transient(exc: BaseException) -> bool:
    return isinstance(exc, _Transient | httpx.TimeoutException | httpx.TransportError)


class ErpClient:
    def __init__(
        self,
        http: Any = None,  # httpx.Client or a compatible client (e.g. Starlette TestClient)
        *,
        base_url: str | None = None,
        attempts: int = 3,
        wait_initial: float = 0.3,
        wait_max: float = 4.0,
        timeout: float = 10.0,
    ) -> None:
        self.http: Any = http or httpx.Client(
            base_url=base_url or get_settings().erp_base_url, timeout=timeout
        )
        self.attempts, self.wait_initial, self.wait_max = attempts, wait_initial, wait_max

    def _request(
        self, method: str, path: str, *, key: str | None = None, json: Any = None
    ) -> httpx.Response:
        headers = {"Idempotency-Key": key} if key else {}
        retrying = Retrying(
            retry=retry_if_exception(_is_transient),
            stop=stop_after_attempt(self.attempts),
            wait=wait_exponential_jitter(initial=self.wait_initial, max=self.wait_max),
            reraise=True,
            before_sleep=lambda rs: log.warning(
                "agent.retry" if "change-requests" in path else "extraction.push_retry",
                path=path,
                attempt=rs.attempt_number,
            ),
        )
        try:
            for attempt in retrying:
                with attempt:
                    resp: httpx.Response = self.http.request(
                        method, path, headers=headers, json=json
                    )
                    if resp.status_code >= 500:
                        raise _Transient(
                            f"ERP {resp.status_code}: {resp.text[:200]}", resp.status_code, True
                        )
        except RetryError as exc:  # pragma: no cover - reraise=True normally prevents this
            raise ErpError(str(exc), None, True) from exc
        except _Transient as exc:
            raise ErpError(str(exc), exc.status, True) from exc
        except httpx.HTTPError as exc:
            raise ErpError(f"ERP unreachable: {type(exc).__name__}", None, True) from exc
        if resp.status_code >= 400:
            raise ErpError(f"ERP {resp.status_code}: {resp.text[:200]}", resp.status_code, False)
        return resp

    def health(self) -> bool:
        try:
            return bool(self.http.get("/health").status_code == 200)
        except httpx.HTTPError:
            return False

    def get_part(self, part_number: str) -> dict[str, Any] | None:
        try:
            return dict(self._request("GET", f"/parts/{part_number}").json())
        except ErpError as exc:
            if exc.status == 404:
                return None
            raise

    def list_parts(self, category: str | None = None) -> list[dict[str, Any]]:
        path = "/parts" + (f"?category={category}" if category else "")
        return list(self._request("GET", path).json())

    def put_part(
        self, part_number: str, spec: dict[str, Any], key: str, lifecycle_status: str | None = None
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"spec": spec}
        if lifecycle_status:
            body["lifecycle_status"] = lifecycle_status
        return dict(self._request("PUT", f"/parts/{part_number}", key=key, json=body).json())

    def create_change_request(self, body: dict[str, Any], key: str) -> dict[str, Any]:
        return dict(self._request("POST", "/change-requests", key=key, json=body).json())

    def get_change_request(self, cid: str) -> dict[str, Any] | None:
        try:
            return dict(self._request("GET", f"/change-requests/{cid}").json())
        except ErpError as exc:
            if exc.status == 404:
                return None
            raise
