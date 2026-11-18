"""structlog JSON logging to stdout and a rotating file; request-scoped context vars."""

from __future__ import annotations

import logging
import re
import sys
from collections.abc import MutableMapping
from logging.handlers import RotatingFileHandler
from typing import Any

import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars

from specbridge.config import get_settings

_SECRET_RE = [
    re.compile(r"sk-ant-[A-Za-z0-9_-]+"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"aws_secret_access_key\s*=\s*\S+", re.I),
]
_SENSITIVE_KEYS = {"x-api-key", "authorization", "api_key", "anthropic_api_key", "password"}


def redact_text(text: str, extra: list[str] | None = None) -> str:
    for rx in _SECRET_RE:
        text = rx.sub("[REDACTED]", text)
    for s in extra or []:
        if s:
            text = text.replace(s, "[REDACTED]")
    return text


def redact_value(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {
            k: "[REDACTED]" if str(k).lower() in _SENSITIVE_KEYS else redact_value(v)
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [redact_value(v) for v in obj]
    if isinstance(obj, str):
        return redact_text(obj)
    return obj


def _redact_processor(
    _: Any, __: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    out = redact_value(dict(event_dict))
    return out  # type: ignore[no-any-return]


def _ensure_context_fields(
    _: Any, __: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """Every line carries request_id/actor/role (null outside a request)."""
    for k in ("request_id", "actor", "role"):
        event_dict.setdefault(k, None)
    return event_dict


def _add_module(_: Any, __: str, event_dict: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
    event_dict.setdefault("module", event_dict.pop("logger", None) or "specbridge")
    return event_dict


_configured = False


def setup_logging(force: bool = False, stdout_level: str | None = None) -> None:
    global _configured
    if _configured and not force:
        return
    s = get_settings()
    level = getattr(logging, s.log_level.upper(), logging.INFO)
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    try:
        s.log_dir.mkdir(parents=True, exist_ok=True)
        handlers.append(
            RotatingFileHandler(
                s.log_dir / "app.jsonl",
                maxBytes=10 * 1024 * 1024,
                backupCount=5,
                encoding="utf-8",
            )
        )
    except OSError:
        pass
    for h in handlers:
        h.setFormatter(logging.Formatter("%(message)s"))
    if stdout_level:
        handlers[0].setLevel(getattr(logging, stdout_level.upper(), logging.WARNING))
    root = logging.getLogger()
    root.handlers = handlers
    root.setLevel(level)
    for noisy in ("httpx", "httpcore", "sentence_transformers", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True, key="ts"),
            structlog.stdlib.add_logger_name,
            _add_module,
            _ensure_context_fields,
            _redact_processor,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(default=str),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,
    )
    _configured = True


def get_logger(name: str = "specbridge") -> Any:
    return structlog.get_logger(name)


def bind_request(request_id: str, actor: str | None = None, role: str | None = None) -> None:
    bind_contextvars(request_id=request_id, actor=actor, role=role)


def clear_request() -> None:
    clear_contextvars()
