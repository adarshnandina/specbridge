"""Cost computation from config/pricing.yaml."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

PRICING_PATH = Path(__file__).resolve().parents[2] / "config" / "pricing.yaml"


@lru_cache
def load_pricing(path: str | None = None) -> dict[str, Any]:
    with open(path or PRICING_PATH, encoding="utf-8") as fh:
        data: dict[str, Any] = yaml.safe_load(fh)
    return data


def compute_cost(
    model: str, input_tokens: int, output_tokens: int, pricing: dict[str, Any] | None = None
) -> float:
    p = pricing or load_pricing()
    entry = p["models"].get(model)
    if entry is None:
        # Unknown model (e.g. fake, or a Bedrock id): fall back to the fake (zero) price entry
        # only for the fake model; otherwise fail loudly so costs are never silently zero.
        if model.startswith("fake"):
            return 0.0
        raise KeyError(f"no pricing for model {model!r} in config/pricing.yaml")
    inp, out = entry["input"], entry["output"]
    thr = entry.get("long_context_threshold_tokens")
    if thr and input_tokens > thr:
        inp, out = entry["long_context_input"], entry["long_context_output"]
    return float((input_tokens * inp + output_tokens * out) / 1_000_000)
