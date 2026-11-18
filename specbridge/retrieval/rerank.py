"""Optional cross-encoder reranker."""

from __future__ import annotations

import threading
from typing import Any, Protocol

from specbridge.config import get_settings


class Reranker(Protocol):
    def score(self, query: str, passages: list[str]) -> list[float]: ...


class CrossEncoderReranker:
    def __init__(self, model_name: str) -> None:
        from sentence_transformers import CrossEncoder

        self.model: Any = CrossEncoder(model_name)

    def score(self, query: str, passages: list[str]) -> list[float]:
        if not passages:
            return []
        return [float(x) for x in self.model.predict([(query, p) for p in passages])]


_lock = threading.Lock()
_reranker: Reranker | None = None


def get_reranker() -> Reranker:
    global _reranker
    with _lock:
        if _reranker is None:
            _reranker = CrossEncoderReranker(get_settings().reranker_model)
        return _reranker


def set_reranker(r: Reranker | None) -> None:
    global _reranker
    _reranker = r
