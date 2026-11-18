import pytest
from pydantic import BaseModel

from specbridge.config import Settings
from specbridge.errors import BudgetExceededError, StructuredOutputError
from specbridge.llm.anthropic_provider import is_retryable
from specbridge.llm.base import LLMRequest
from specbridge.llm.budget import BudgetGuard
from specbridge.llm.cache import ResponseCache
from specbridge.llm.fake_provider import FakeProvider
from specbridge.llm.pricing import compute_cost
from specbridge.llm.usage import LLMService, MemoryLedger

PRICING = {
    "models": {
        "m": {"input": 1.0, "output": 2.0},
        "tiered": {
            "input": 0.1,
            "output": 0.5,
            "long_context_threshold_tokens": 100,
            "long_context_input": 0.5,
            "long_context_output": 2.5,
        },
    }
}


class Out(BaseModel):
    answer: str


def make(provider=None, budget=5.0, cache=None):
    ledger = MemoryLedger()
    s = Settings(_env_file=None, log_llm_payloads=False)
    svc = LLMService(
        provider or FakeProvider(),
        settings=s,
        recorder=ledger.record,
        budget=BudgetGuard(budget, ledger.spent),
        cache=cache,
        pricing=PRICING,
        request_id_getter=lambda: "rid",
    )
    return svc, ledger


def test_cost_basic_and_tiered():
    assert compute_cost("m", 1_000_000, 500_000, PRICING) == pytest.approx(2.0)
    assert compute_cost("tiered", 50, 10, PRICING) == pytest.approx((50 * 0.1 + 10 * 0.5) / 1e6)
    assert compute_cost("tiered", 200, 10, PRICING) == pytest.approx((200 * 0.5 + 10 * 2.5) / 1e6)
    with pytest.raises(KeyError):
        compute_cost("unknown", 1, 1, PRICING)


def test_real_pricing_file_loads():
    assert compute_cost("claude-haiku-5-5", 100_000, 0) == pytest.approx(0.01)
    assert compute_cost("claude-haiku-5-5", 200_000, 0) == pytest.approx(0.10)
    assert compute_cost("claude-sonnet-5-5", 0, 1_000_000) == pytest.approx(10.0)


def test_budget_guard():
    g = BudgetGuard(1.0, lambda: 0.9)
    g.check(0.05)
    with pytest.raises(BudgetExceededError):
        g.check(0.2)


def test_fake_structured_and_accounting():
    p = FakeProvider()
    p.script("qa", {"answer": "42"})
    svc, ledger = make(p)
    out = svc.structured(
        Out,
        tool_name="submit",
        tool_description="d",
        system="s",
        messages=[{"role": "user", "content": "q"}],
        purpose="qa",
        prompt_version="qa.v1",
    )
    assert out.answer == "42"
    row = ledger.rows[0]
    assert row["purpose"] == "qa" and row["prompt_version"] == "qa.v1"
    assert row["request_id"] == "rid" and row["cost_usd"] == 0.0 and row["input_tokens"] > 0


def test_structured_retries_once_then_succeeds():
    p = FakeProvider()
    p.script("qa", {"wrong": 1}, {"answer": "ok"})
    svc, ledger = make(p)
    out = svc.structured(
        Out,
        tool_name="submit",
        tool_description="d",
        system="",
        messages=[{"role": "user", "content": "q"}],
        purpose="qa",
    )
    assert out.answer == "ok" and len(ledger.rows) == 2
    assert "invalid" in p.calls[1].messages[-1]["content"]


def test_structured_fails_after_two_invalid():
    p = FakeProvider()
    p.script("qa", {"x": 1}, {"y": 2})
    svc, _ = make(p)
    with pytest.raises(StructuredOutputError):
        svc.structured(
            Out,
            tool_name="submit",
            tool_description="d",
            system="",
            messages=[{"role": "user", "content": "q"}],
            purpose="qa",
        )


def test_budget_blocks_call():
    svc, ledger = make(budget=0.0)
    ledger.rows.append({"cost_usd": 1.0})
    with pytest.raises(BudgetExceededError):
        svc.complete(LLMRequest(messages=[], purpose="qa"))


def test_cache_hit_flagged_and_free(tmp_path):
    p = FakeProvider()
    p.script("qa", "hello")
    svc, ledger = make(p, cache=ResponseCache(tmp_path / "c.sqlite"))
    r1 = svc.complete(LLMRequest(messages=[{"role": "user", "content": "q"}], purpose="qa"))
    r2 = svc.complete(LLMRequest(messages=[{"role": "user", "content": "q"}], purpose="qa"))
    assert not r1.cache_hit and r2.cache_hit and r2.text == "hello"
    assert [r["cache_hit"] for r in ledger.rows] == [False, True]
    assert len(p.calls) == 1


def test_provider_error_is_recorded():
    p = FakeProvider()
    p.script("qa", RuntimeError("boom"))
    svc, ledger = make(p)
    with pytest.raises(RuntimeError):
        svc.complete(LLMRequest(messages=[], purpose="qa"))
    assert ledger.rows[0]["status"] == "error"


def test_retryable_classification():
    import anthropic
    import httpx

    req = httpx.Request("POST", "http://x")

    def status(code):
        return anthropic.APIStatusError("e", response=httpx.Response(code, request=req), body=None)

    assert is_retryable(status(503)) and is_retryable(status(429))
    assert not is_retryable(status(400)) and not is_retryable(ValueError())


def test_unpriced_model_is_refused_before_any_call():
    from specbridge.llm.base import LLMResult
    from specbridge.llm.pricing import ensure_priced, resolve_model

    class Paid(FakeProvider):
        name = "anthropic"

    p = Paid()
    p.script("qa", "hi")
    svc, ledger = make(p)
    svc.pricing = PRICING
    with pytest.raises(KeyError, match="no pricing"):
        svc.complete(LLMRequest(messages=[], purpose="qa", model="some.bedrock.model-v1"))
    assert p.calls == [] and ledger.rows == []  # nothing was called or spent
    aliased = {**PRICING, "aliases": {"some.bedrock.model-v1": "m"}}
    ensure_priced("some.bedrock.model-v1", aliased)
    assert resolve_model("some.bedrock.model-v1", aliased) == "m"
    assert compute_cost("some.bedrock.model-v1", 1_000_000, 0, aliased) == pytest.approx(1.0)
    svc.pricing = aliased
    res = svc.complete(LLMRequest(messages=[], purpose="qa", model="some.bedrock.model-v1"))
    assert isinstance(res, LLMResult)
    assert ledger.rows[0]["cost_usd"] > 0 and ledger.rows[0]["model"] == "some.bedrock.model-v1"
