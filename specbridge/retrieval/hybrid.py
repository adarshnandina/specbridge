"""Reciprocal Rank Fusion."""

from __future__ import annotations

from collections.abc import Hashable, Sequence


def rrf[K: Hashable](rankings: Sequence[Sequence[K]], k: int = 60) -> list[tuple[K, float]]:
    """Fuse ranked id lists: score(d) = sum 1/(k + rank). Ties broken by first appearance."""
    scores: dict[K, float] = {}
    first: dict[K, int] = {}
    n = 0
    for ranking in rankings:
        for rank, item in enumerate(ranking, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank)
            if item not in first:
                first[item] = n
                n += 1
    return sorted(scores.items(), key=lambda kv: (-kv[1], first[kv[0]]))
