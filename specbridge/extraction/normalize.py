"""Normalise raw ComponentSpec values to canonical units/names (deterministic, no LLM)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from specbridge.extraction import units as U
from specbridge.extraction.fields import ALL_FIELDS
from specbridge.extraction.schema import ComponentSpec, FieldValue, ValidationIssue

PAIRS = {
    "supply_voltage_min_v": 0,
    "supply_voltage_max_v": 1,
    "operating_temp_min_c": 0,
    "operating_temp_max_c": 1,
}
_UNIT_IN_TEXT = re.compile(r"(?<![A-Za-z])(mA|µA|kW|mW|kg|mV|kV|°F|K|cm|in|m)(?![A-Za-z])")


@dataclass
class Normalized:
    data: dict[str, Any]
    evidence: dict[str, dict[str, Any]] = field(default_factory=dict)
    issues: list[ValidationIssue] = field(default_factory=list)


def _first_number(fv: FieldValue, key: str) -> tuple[float | None, str | None]:
    v = fv.value
    if v is None:
        return None, None
    unit = fv.unit
    if isinstance(v, int | float):
        return float(v), unit
    if isinstance(v, list):
        nums = [float(x) for x in v if isinstance(x, int | float)]
        if len(nums) == 2 and key in PAIRS:
            return nums[PAIRS[key]], unit
        return (nums[0] if nums else None), unit
    text = str(v)
    if not unit:
        m = _UNIT_IN_TEXT.search(text)
        unit = m.group(1) if m else None
        if unit is None and "°C" in text:
            unit = "°C"
    if key in PAIRS:
        rng = U.parse_range(text)
        if rng:
            return rng[PAIRS[key]], unit
    nums = U.numbers_in(text)
    return (nums[0] if nums else None), unit


def normalize_spec(spec: ComponentSpec) -> Normalized:
    out = Normalized(data={f: None for f in ALL_FIELDS})
    raw: dict[str, FieldValue | None] = dict(spec)
    for key in ALL_FIELDS:
        fv = raw.get(key)
        if fv is None or fv.value in (None, "", []):
            continue
        try:
            val = _normalize_field(key, fv, out)
        except Exception as exc:  # defensive: a malformed value must not crash the pipeline
            out.issues.append(
                ValidationIssue(
                    field=key,
                    rule="normalization",
                    message=f"could not normalise {fv.value!r}: {exc}",
                )
            )
            continue
        if val is not None:
            out.data[key] = val
            out.evidence[key] = {"page": fv.page, "quote": fv.quote}
    return out


def _normalize_field(key: str, fv: FieldValue, out: Normalized) -> Any:
    v = fv.value
    if key in ("part_number",):
        return re.sub(r"\s+", "", str(v)) or None
    if key in ("manufacturer", "product_name", "datasheet_revision"):
        s = " ".join(str(v).split())
        if key == "datasheet_revision":
            m = re.search(r"\d+(?:\.\d+)*", s)
            return m.group(0) if m else s
        return s or None
    if key == "category":
        return U.canonical_category(str(v))
    if key == "ip_rating":
        ip = U.normalize_ip(str(v))
        return ip or re.sub(r"\s+", "", str(v)).upper()
    if key == "interfaces":
        return U.canonical_interfaces(v if isinstance(v, list) else str(v)) or None
    if key == "certifications":
        return U.canonical_certs(v if isinstance(v, list) else str(v)) or None
    if key == "dimensions_mm":
        nums = (
            [float(x) for x in v if isinstance(x, int | float)]
            if isinstance(v, list)
            else U.numbers_in(str(v))
        )
        unit = fv.unit
        if not unit and not isinstance(v, list):
            m = _UNIT_IN_TEXT.search(str(v))
            unit = m.group(1) if m else None
        conv = [U.convert(n, unit, "mm") for n in nums]
        if any(c is None for c in conv):
            out.issues.append(
                ValidationIssue(
                    field=key, rule="unit_conversion", message=f"cannot convert unit {unit!r} to mm"
                )
            )
            return None
        return [_clean(float(c)) for c in conv if c is not None]
    target = U.UNIT_TARGETS[key]
    num, unit = _first_number(fv, key)
    if num is None:
        out.issues.append(
            ValidationIssue(
                field=key, rule="not_numeric", message=f"no number found in {fv.value!r}"
            )
        )
        return None
    conv_v = U.convert(num, unit, target)
    if conv_v is None:
        out.issues.append(
            ValidationIssue(
                field=key,
                rule="unit_conversion",
                message=f"cannot convert unit {unit!r} to {target}",
            )
        )
        return None
    return _clean(conv_v)


def _clean(x: float) -> float | int:
    x = round(x, 6)
    return int(x) if float(x).is_integer() else x
