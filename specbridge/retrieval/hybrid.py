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


def competition_ranks[K: Hashable](scored: Sequence[tuple[K, float]]) -> dict[K, int]:
    """Rank by descending score; tied scores share the best rank (1, 2, 2, 4 ...).

    Used before fusion so that an arbitrary order among equal scores (e.g. many chunks with the
    same full-text rank) carries no weight in RRF.
    """
    ordered = sorted(scored, key=lambda kv: -kv[1])
    ranks: dict[K, int] = {}
    for i, (item, score) in enumerate(ordered):
        ranks[item] = 1 + sum(1 for _, s in ordered if s > score) if i else 1
    return ranks


def rrf_scored[K: Hashable](
    lists: Sequence[Sequence[tuple[K, float]]], k: int = 60
) -> list[tuple[K, float]]:
    """RRF over (id, score) lists using tie-aware ranks. Ties in the fused score keep the input
    (already deterministic) order of first appearance."""
    rank_maps = [competition_ranks(lst) for lst in lists]
    scores: dict[K, float] = {}
    first: dict[K, int] = {}
    n = 0
    for lst, ranks in zip(lists, rank_maps, strict=True):
        for item, _ in lst:
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + ranks[item])
            if item not in first:
                first[item] = n
                n += 1
    return sorted(scores.items(), key=lambda kv: (-kv[1], first[kv[0]]))
