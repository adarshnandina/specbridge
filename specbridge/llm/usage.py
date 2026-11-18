"""LLMService: budget guard + cache + provider call + usage accounting + structured output."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError
from sqlalchemy import func, select

from specbridge import metrics
from specbridge.config import Settings, get_settings
from specbridge.db.models import LLMCall
from specbridge.db.session import session_scope
from specbridge.errors import StructuredOutputError
from specbridge.llm.base import LLMProvider, LLMRequest, LLMResult, forced, pydantic_tool
from specbridge.llm.budget import BudgetGuard
from specbridge.llm.cache import ResponseCache, cache_key
from specbridge.llm.pricing import compute_cost, ensure_priced
from specbridge.logging_setup import get_logger, redact_text

log = get_logger("specbridge.llm")
T = TypeVar("T", bound=BaseModel)

Recorder = Callable[[dict[str, Any]], None]


def db_recorder(row: dict[str, Any]) -> None:
    with session_scope() as s:
        s.add(LLMCall(**row))


def db_spent_today() -> float:
    start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    with session_scope() as s:
        v = s.execute(
            select(func.coalesce(func.sum(LLMCall.cost_usd), 0.0)).where(LLMCall.ts >= start)
        )
        return float(v.scalar_one())


class MemoryLedger:
    """In-memory recorder + spend tracker (unit tests, eval runs without DB writes)."""

    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def record(self, row: dict[str, Any]) -> None:
        self.rows.append(row)

    def spent(self) -> float:
        return float(sum(r["cost_usd"] for r in self.rows))


class LLMService:
    def __init__(
        self,
        provider: LLMProvider,
        settings: Settings | None = None,
        recorder: Recorder | None = None,
        budget: BudgetGuard | None = None,
        cache: ResponseCache | None = None,
        pricing: dict[str, Any] | None = None,
        request_id_getter: Callable[[], str | None] | None = None,
    ) -> None:
        self.provider = provider
        self.settings = settings or get_settings()
        self.recorder = recorder or db_recorder
        self.budget = budget or BudgetGuard(self.settings.llm_daily_budget_usd, db_spent_today)
        self.cache = cache
        self.pricing = pricing
        self.request_id_getter = request_id_getter or _ctx_request_id
        self.session_cost = 0.0
        self.session_calls: list[dict[str, Any]] = []

    # ------------------------------------------------------------------ core
    def complete(self, req: LLMRequest) -> LLMResult:
        if not req.model:
            req.model = self.settings.model_for(req.purpose)
        if self.provider.name != "fake":
            ensure_priced(req.model, self.pricing)
        self.budget.check()
        key = cache_key(self.provider.name, req) if self.cache else None
        status, error = "ok", None
        t0 = time.perf_counter()
        res: LLMResult | None = None
        try:
            if self.cache and key:
                hit = self.cache.get(key)
                if hit:
                    hit.cache_hit = True
                    res = hit
            if res is None:
                res = self.provider.complete(req)
                if self.cache and key:
                    self.cache.put(key, res)
            return res
        except Exception as exc:
            status, error = "error", redact_text(str(exc))[:500]
            raise
        finally:
            self._account(req, res, status, error, int((time.perf_counter() - t0) * 1000))

    def _account(
        self, req: LLMRequest, res: LLMResult | None, status: str, error: str | None, wall_ms: int
    ) -> None:
        try:
            in_t = res.input_tokens if res else 0
            out_t = res.output_tokens if res else 0
            hit = bool(res and res.cache_hit)
            cost = (
                0.0
                if (hit or not res or self.provider.name == "fake")
                else compute_cost(req.model, in_t, out_t, self.pricing)
            )
            row = {
                "request_id": self.request_id_getter(),
                "purpose": req.purpose,
                "provider": self.provider.name,
                "model": req.model,
                "prompt_version": req.prompt_version,
                "input_tokens": in_t,
                "output_tokens": out_t,
                "cost_usd": cost,
                "latency_ms": res.latency_ms if res and not hit else wall_ms,
                "cache_hit": hit,
                "status": status,
                "error": error,
            }
            self.session_cost += cost
            self.session_calls.append(row)
            self.recorder(row)
            metrics.LLM_CALLS.labels(req.purpose, req.model, status).inc()
            metrics.LLM_TOKENS.labels(req.purpose, req.model, "input").inc(in_t)
            metrics.LLM_TOKENS.labels(req.purpose, req.model, "output").inc(out_t)
            metrics.LLM_COST.labels(req.purpose, req.model).inc(cost)
            metrics.BUDGET_REMAINING.set(self.budget.remaining())
            log.info(
                "llm.call",
                purpose=req.purpose,
                model=req.model,
                prompt_version=req.prompt_version,
                input_tokens=in_t,
                output_tokens=out_t,
                cost_usd=cost,
                latency_ms=row["latency_ms"],
                cache_hit=hit,
                status=status,
            )
            if self.settings.log_llm_payloads:
                self._log_payload(req, res)
        except Exception as exc:  # accounting must never break the call path
            log.error("llm.accounting_failed", error=str(exc))

    def _log_payload(self, req: LLMRequest, res: LLMResult | None) -> None:
        path = self.settings.log_dir / "llm_payloads.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        rec = {
            "ts": datetime.now(UTC).isoformat(),
            "purpose": req.purpose,
            "model": req.model,
            "system": req.system,
            "messages": req.messages,
            "response_text": res.text if res else None,
            "tool_calls": [t.input for t in res.tool_calls] if res else None,
        }
        keys = [self.settings.anthropic_api_key]
        with path.open("a", encoding="utf-8") as fh:
            fh.write(redact_text(json.dumps(rec, default=str), keys) + "\n")

    # ------------------------------------------------------- structured output
    def structured(
        self,
        model_cls: type[T],
        *,
        tool_name: str,
        tool_description: str,
        system: str,
        messages: list[dict[str, Any]],
        purpose: str,
        prompt_version: str | None = None,
        max_tokens: int = 2048,
    ) -> T:
        """Forced tool use; parse with Pydantic; retry once with the validation error appended."""
        tools = [pydantic_tool(tool_name, tool_description, model_cls)]
        msgs = list(messages)
        last_err = ""
        for attempt in range(2):
            req = LLMRequest(
                messages=msgs,
                system=system,
                tools=tools,
                tool_choice=forced(tool_name),
                max_tokens=max_tokens,
                purpose=purpose,
                prompt_version=prompt_version,
            )
            res = self.complete(req)
            call = next((c for c in res.tool_calls if c.name == tool_name), None)
            try:
                if call is None:
                    raise ValueError(f"model did not call tool {tool_name!r}")
                return model_cls.model_validate(call.input)
            except (ValidationError, ValueError) as exc:
                last_err = str(exc)
                log.warning("llm.structured_invalid", purpose=purpose, attempt=attempt + 1)
                msgs = [
                    *messages,
                    {
                        "role": "user",
                        "content": (
                            f"Your previous tool call was invalid: {last_err[:800]}\n"
                            f"Call {tool_name} again with valid input."
                        ),
                    },
                ]
        raise StructuredOutputError(
            f"LLM returned invalid structured output twice for {purpose}: {last_err[:300]}"
        )


def _ctx_request_id() -> str | None:
    from structlog.contextvars import get_contextvars

    v = get_contextvars().get("request_id")
    return str(v) if v else None


def build_provider(settings: Settings | None = None) -> LLMProvider:
    s = settings or get_settings()
    if s.llm_provider == "anthropic":
        from specbridge.llm.anthropic_provider import AnthropicProvider

        return AnthropicProvider()
    if s.llm_provider == "bedrock":
        from specbridge.llm.anthropic_provider import BedrockProvider

        return BedrockProvider()
    from specbridge.llm.fake_provider import FakeProvider

    return FakeProvider()
