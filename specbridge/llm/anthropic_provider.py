"""Anthropic and Bedrock providers (same Messages API surface)."""

from __future__ import annotations

import time
from typing import Any

import anthropic
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

from specbridge.config import get_settings
from specbridge.llm.base import LLMRequest, LLMResult, ToolCall


def is_retryable(exc: BaseException) -> bool:
    """Retry on rate limits, 5xx, timeouts and connection errors; never on other 4xx."""
    if isinstance(
        exc, anthropic.RateLimitError | anthropic.APITimeoutError | anthropic.APIConnectionError
    ):
        return True
    if isinstance(exc, anthropic.APIStatusError):
        return exc.status_code >= 500 or exc.status_code == 429
    return False


class _AnthropicLike:
    name = "anthropic"

    def __init__(self, client: Any, max_retries: int | None = None) -> None:
        self.client = client
        self.max_retries = get_settings().llm_max_retries if max_retries is None else max_retries

    def _call(self, kwargs: dict[str, Any]) -> Any:
        @retry(
            retry=retry_if_exception(is_retryable),
            stop=stop_after_attempt(self.max_retries + 1),
            wait=wait_exponential_jitter(initial=0.5, max=8),
            reraise=True,
        )
        def go() -> Any:
            return self.client.messages.create(**kwargs)

        return go()

    def complete(self, req: LLMRequest) -> LLMResult:
        kwargs: dict[str, Any] = {
            "model": req.model,
            "max_tokens": req.max_tokens,
            "temperature": req.temperature,
            "messages": req.messages,
        }
        if req.system:
            kwargs["system"] = req.system
        if req.tools:
            kwargs["tools"] = req.tools
        if req.tool_choice:
            kwargs["tool_choice"] = req.tool_choice
        t0 = time.perf_counter()
        resp = self._call(kwargs)
        latency = int((time.perf_counter() - t0) * 1000)
        text, calls = "", []
        for block in resp.content:
            if block.type == "text":
                text += block.text
            elif block.type == "tool_use":
                calls.append(ToolCall(name=block.name, input=dict(block.input), id=block.id))
        return LLMResult(
            text=text,
            tool_calls=calls,
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
            model=req.model,
            latency_ms=latency,
            provider=self.name,
        )


class AnthropicProvider(_AnthropicLike):
    name = "anthropic"

    def __init__(self, api_key: str | None = None, client: Any = None) -> None:
        s = get_settings()
        key = api_key or s.anthropic_api_key
        if client is None:
            if not key:
                raise RuntimeError("ANTHROPIC_API_KEY is not set")
            client = anthropic.Anthropic(api_key=key, timeout=s.llm_timeout_s, max_retries=0)
        super().__init__(client)


class BedrockProvider(_AnthropicLike):
    name = "bedrock"

    def __init__(self, client: Any = None) -> None:
        s = get_settings()
        if client is None:
            client = anthropic.AnthropicBedrock(
                aws_region=s.aws_region, timeout=s.llm_timeout_s, max_retries=0
            )
        super().__init__(client)
