"""Small statistics helpers: Wilson intervals, percentiles, noise flags."""

from __future__ import annotations

import math
from typing import Any


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a proportion k/n."""
    if n <= 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def proportion(k: int, n: int) -> dict[str, Any]:
    lo, hi = wilson(k, n)
    return {"value": (k / n) if n else None, "k": k, "n": n, "ci": [round(lo, 4), round(hi, 4)]}


def percentile(values: list[float], q: float) -> float | None:
    """Linear-interpolated percentile (q in 0..100)."""
    if not values:
        return None
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    pos = (len(xs) - 1) * q / 100
    lo, hi = math.floor(pos), math.ceil(pos)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def overlap_fraction(a: list[float], b: list[float]) -> float:
    """Overlap length of two intervals relative to the narrower one (0..1)."""
    lo, hi = max(a[0], b[0]), min(a[1], b[1])
    if hi <= lo:
        return 0.0
    narrow = min(a[1] - a[0], b[1] - b[0])
    return 1.0 if narrow <= 0 else min(1.0, (hi - lo) / narrow)


def noise_flag(a: dict[str, Any], b: dict[str, Any]) -> str:
    """'significant' (disjoint CIs), 'weak' (partial overlap), 'within noise' (>=50% overlap)."""
    if a.get("value") is None or b.get("value") is None or "ci" not in a or "ci" not in b:
        return "n/a"
    f = overlap_fraction(a["ci"], b["ci"])
    if f == 0.0:
        return "significant"
    return "within noise" if f >= 0.5 else "weak"
