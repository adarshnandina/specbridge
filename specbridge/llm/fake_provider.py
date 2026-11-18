"""Deterministic, scriptable provider used by tests, CI and offline evals."""

from __future__ import annotations

import hashlib
import json
from collections import deque
from collections.abc import Callable
from typing import Any

from specbridge.llm.base import LLMRequest, LLMResult, ToolCall

Handler = Callable[[LLMRequest], "LLMResult | dict[str, Any] | str"]


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def request_hash(req: LLMRequest) -> str:
    blob = json.dumps(
        [req.purpose, req.system, req.messages, req.tool_choice], sort_keys=True, default=str
    )
    return hashlib.sha256(blob.encode()).hexdigest()


class FakeProvider:
    """Responses come from (in priority order): a scripted queue per purpose, a handler per
    purpose, then an error. A dict return value is treated as the forced tool's input."""

    name = "fake"

    def __init__(self) -> None:
        self.handlers: dict[str, Handler] = {}
        self.queues: dict[str, deque[Any]] = {}
        self.calls: list[LLMRequest] = []

    def register(self, purpose: str, handler: Handler) -> None:
        self.handlers[purpose] = handler

    def script(self, purpose: str, *responses: Any) -> None:
        """Queue responses (dict tool input / str text / LLMResult / Exception) for a purpose."""
        self.queues.setdefault(purpose, deque()).extend(responses)

    def complete(self, req: LLMRequest) -> LLMResult:
        self.calls.append(req)
        q = self.queues.get(req.purpose)
        if q:
            item = q.popleft()
        elif req.purpose in self.handlers:
            item = self.handlers[req.purpose](req)
        else:
            raise RuntimeError(f"FakeProvider has no handler/script for purpose {req.purpose!r}")
        if isinstance(item, Exception):
            raise item
        return self._wrap(item, req)

    def _wrap(self, item: Any, req: LLMRequest) -> LLMResult:
        in_tok = estimate_tokens(req.system + json.dumps(req.messages, default=str))
        if isinstance(item, LLMResult):
            res = item
        elif isinstance(item, dict) and "tool_calls" in item and "text" in item:
            res = LLMResult(
                text=item["text"],
                tool_calls=[ToolCall(**tc) for tc in item["tool_calls"]],
            )
        elif isinstance(item, dict):
            name = (req.tool_choice or {}).get("name") or (
                req.tools[0]["name"] if req.tools else "tool"
            )
            res = LLMResult(tool_calls=[ToolCall(name=name, input=item)])
        else:
            res = LLMResult(text=str(item))
        res.model = req.model or "fake-model"
        res.provider = "fake"
        res.input_tokens = res.input_tokens or in_tok
        res.output_tokens = res.output_tokens or estimate_tokens(
            res.text + json.dumps([t.input for t in res.tool_calls], default=str)
        )
        res.latency_ms = res.latency_ms or 1
        return res
