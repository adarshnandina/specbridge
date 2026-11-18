"""Fake-provider responders for extraction (filled in during M3)."""

from __future__ import annotations

from specbridge.llm.fake_provider import FakeProvider


def register_extraction_handlers(fake: FakeProvider) -> FakeProvider:
    return fake
