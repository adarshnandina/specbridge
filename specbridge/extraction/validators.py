"""Deterministic validation of normalised specs (no LLM confidence is ever used as a gate)."""

from __future__ import annotations

import re
from typing import Any

from specbridge.extraction import units as U
from specbridge.extraction.fields import (
    ALL_FIELDS,
    CATEGORIES,
    NUMERIC_FIELDS,
    REQUIRED_FIELDS,
)
from specbridge.extraction.schema import ValidationIssue
from specbridge.qa.citations import normalize, quote_matches

EVIDENCE_THRESHOLD = 85.0
PLAUSIBLE = {
    "operating_temp_min_c": (-273.0, 500.0),
    "operating_temp_max_c": (-273.0, 500.0),
    "supply_voltage_min_v": (0.0, 1000.0),
    "supply_voltage_max_v": (0.0, 1000.0),
    "rated_current_a": (0.0, 1000.0),
    "power_w": (0.0, 10_000_000.0),
    "weight_g": (0.0, 1e7),
}
IP_RE = re.compile(r"^IP[0-6][0-9]K?$")
SCALES = (1.0, 1e-3, 1e3, 1e-6, 1e6)


def _issue(f: str, rule: str, msg: str, sev: str = "error") -> ValidationIssue:
    return ValidationIssue(field=f, rule=rule, message=msg, severity=sev)


def _value_numbers(v: Any) -> list[float]:
    if isinstance(v, list):
        return [float(x) for x in v]
    return [float(v)]


def _numbers_supported(values: list[float], quote: str) -> bool:
    qn = U.numbers_in(quote)
    pool = set()
    for n in qn:
        for s in SCALES:
            pool.add(round(n * s, 6))
            pool.add(round(abs(n) * s, 6))
    # temperatures converted from other scales are not supported by the quote: flagged
    return all(
        round(abs(v), 6) in pool
        or round(v, 6) in pool
        or any(abs(v - p) <= 1e-6 * max(1.0, abs(v)) for p in pool)
        for v in values
    )


def validate(
    data: dict[str, Any], evidence: dict[str, dict[str, Any]], page_texts: dict[int, str]
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for f in REQUIRED_FIELDS:
        if not data.get(f):
            issues.append(_issue(f, "required", f"{f} is required"))
    for lo, hi in (
        ("supply_voltage_min_v", "supply_voltage_max_v"),
        ("operating_temp_min_c", "operating_temp_max_c"),
    ):
        if data.get(lo) is not None and data.get(hi) is not None and data[lo] > data[hi]:
            issues.append(_issue(lo, "min_le_max", f"{lo} ({data[lo]}) > {hi} ({data[hi]})"))
    for f, (a, b) in PLAUSIBLE.items():
        v = data.get(f)
        if v is not None and not (a <= v <= b):
            issues.append(_issue(f, "plausibility", f"{f}={v} outside plausible range [{a}, {b}]"))
    ip = data.get("ip_rating")
    if ip is not None and not IP_RE.match(str(ip)):
        issues.append(
            _issue("ip_rating", "ip_format", f"ip_rating {ip!r} does not match IP[0-6][0-9]K?")
        )
    cat = data.get("category")
    if cat is not None and cat not in CATEGORIES:
        issues.append(_issue("category", "category_enum", f"unknown category {cat!r}"))
    dims = data.get("dimensions_mm")
    if dims is not None and (len(dims) != 3 or any(d <= 0 for d in dims)):
        issues.append(
            _issue("dimensions_mm", "dimensions", "need three positive numbers [w, h, d]")
        )

    # evidence check
    for f in ALL_FIELDS:
        v = data.get(f)
        if v is None:
            continue
        ev = evidence.get(f) or {}
        page, quote = ev.get("page"), ev.get("quote")
        if not quote or page is None:
            issues.append(_issue(f, "evidence_missing", f"{f} has no page/quote evidence"))
            continue
        text = page_texts.get(int(page))
        if text is None:
            issues.append(_issue(f, "evidence_page", f"{f}: cited page {page} does not exist"))
            continue
        if not quote_matches(quote, text, EVIDENCE_THRESHOLD):
            issues.append(_issue(f, "evidence_quote", f"{f}: quote not found on page {page}"))
            continue
        if f in NUMERIC_FIELDS or f == "dimensions_mm":
            if not _numbers_supported(_value_numbers(v), quote):
                issues.append(
                    _issue(f, "evidence_number", f"{f}={v}: numbers not found in quote {quote!r}")
                )
        elif f == "part_number":
            if normalize(str(v)).replace(" ", "") not in normalize(text).replace(" ", ""):
                issues.append(_issue(f, "evidence_value", f"part number {v!r} not on page {page}"))
        elif f == "ip_rating" and str(v) not in U.all_ips(quote):
            issues.append(_issue(f, "evidence_value", f"{v} not in quote {quote!r}"))

    # category consistency (warnings only)
    if cat == "drive" and data.get("power_w") is None and data.get("rated_current_a") is None:
        issues.append(
            _issue(
                "category",
                "category_consistency",
                "drive without power or current rating",
                "warning",
            )
        )
    if (
        cat == "power_supply"
        and data.get("rated_current_a") is None
        and data.get("power_w") is None
    ):
        issues.append(
            _issue(
                "category",
                "category_consistency",
                "power supply without current or power rating",
                "warning",
            )
        )
    if cat == "sensor" and (data.get("power_w") or 0) > 100:
        issues.append(
            _issue(
                "category",
                "category_consistency",
                "sensor with power > 100 W is unusual",
                "warning",
            )
        )
    return issues


def errors(issues: list[ValidationIssue]) -> list[ValidationIssue]:
    return [i for i in issues if i.severity == "error"]
