# 0004 - LLM provider abstraction (Anthropic / Bedrock / Fake)

## Context
The system must run against the Anthropic API, AWS Bedrock, and offline in CI, with cost control and
reproducible tests. No test may call a real LLM.

## Options considered
Call the SDK directly everywhere; a thin protocol with swappable providers plus a wrapper that adds
accounting; a third-party router library.

## Decision
`LLMProvider.complete(LLMRequest) -> LLMResult` with `AnthropicProvider`, `BedrockProvider` (same
Messages API surface via `AnthropicBedrock`) and a scriptable `FakeProvider`. `LLMService` wraps any
provider with: daily budget guard, optional SQLite response cache (hits flagged and excluded from
latency stats), a `llm_calls` row + structured log + Prometheus counters per call, redacted payload
logging, and structured output via forced tool use validated with Pydantic (one retry with the
validation error appended, then `StructuredOutputError`). Prices come from `config/pricing.yaml`
(verified 2026-11-18 on the Anthropic pricing page); an unknown priced model raises instead of
reporting zero cost. Fake responders (extractive QA, rule-based extraction, agent parse/compare)
let every pipeline run offline.

## Consequences
- Tests, CI and the agent safety scenarios need no API key; paid runs are gated by cost estimates.
- Fake-provider metrics are **pipeline checks only** and are labelled as such in every result file.
- The pricing page lists names and prices but not API model IDs; IDs come from the build environment
  and must be re-checked before the first paid run.
