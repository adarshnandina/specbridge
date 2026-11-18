"""Embedding model wrapper. EMBEDDING_MODEL=hash selects an offline embedder (tests)."""

from __future__ import annotations

import hashlib
import math
import re
import threading
from typing import Protocol

from specbridge.config import get_settings


class Embedder(Protocol):
    dim: int

    def embed(self, texts: list[str], batch_size: int = 32) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...
    def token_count(self, text: str) -> int: ...


class HashEmbedder:
    """Bag-of-words hashing embedder: deterministic, no downloads. Tests/CI only."""

    def __init__(self, dim: int = 384) -> None:
        self.dim = dim

    def _vec(self, text: str) -> list[float]:
        v = [0.0] * self.dim
        for tok in re.findall(r"\w+", text.lower()):
            h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
            v[h % self.dim] += 1.0
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / n for x in v]

    def embed(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vec(text)

    def token_count(self, text: str) -> int:
        return len(re.findall(r"\w+|[^\w\s]", text))


class SentenceTransformerEmbedder:
    QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

    def __init__(self, model_name: str) -> None:
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_name)
        self.dim = int(self.model.get_sentence_embedding_dimension() or 0)
        self.tokenizer = self.model.tokenizer

    def embed(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        arr = self.model.encode(
            texts, batch_size=batch_size, normalize_embeddings=True, show_progress_bar=False
        )
        return [list(map(float, row)) for row in arr]

    def embed_query(self, text: str) -> list[float]:
        return self.embed([self.QUERY_PREFIX + text])[0]

    def token_count(self, text: str) -> int:
        return len(self.tokenizer.encode(text, add_special_tokens=False))


_lock = threading.Lock()
_embedder: Embedder | None = None


def get_embedder() -> Embedder:
    global _embedder
    with _lock:
        if _embedder is None:
            s = get_settings()
            emb: Embedder
            if s.embedding_model == "hash":
                emb = HashEmbedder(s.embedding_dim)
            else:
                emb = SentenceTransformerEmbedder(s.embedding_model)
            if emb.dim != s.embedding_dim:
                raise RuntimeError(
                    f"Embedding model dim {emb.dim} != EMBEDDING_DIM {s.embedding_dim}"
                )
            _embedder = emb
        return _embedder


def set_embedder(e: Embedder | None) -> None:
    global _embedder
    _embedder = e


def embedder_loaded() -> bool:
    return _embedder is not None
