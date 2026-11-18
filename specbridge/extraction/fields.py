"""Canonical ComponentSpec field names and small shared helpers (no heavy imports)."""

from __future__ import annotations

import re
from typing import Any

CATEGORIES = ("sensor", "drive", "io_module", "power_supply", "other")

# Normalized (flat) spec keys. Values are canonical units: V, A, W, degC, mm, g.
SCALAR_FIELDS = (
    "part_number",
    "manufacturer",
    "product_name",
    "category",
    "supply_voltage_min_v",
    "supply_voltage_max_v",
    "rated_current_a",
    "power_w",
    "operating_temp_min_c",
    "operating_temp_max_c",
    "ip_rating",
    "weight_g",
    "datasheet_revision",
)
LIST_FIELDS = ("certifications", "interfaces")
DIM_FIELD = "dimensions_mm"  # list [w, h, d]
ALL_FIELDS = SCALAR_FIELDS + LIST_FIELDS + (DIM_FIELD,)
NUMERIC_FIELDS = (
    "supply_voltage_min_v",
    "supply_voltage_max_v",
    "rated_current_a",
    "power_w",
    "operating_temp_min_c",
    "operating_temp_max_c",
    "weight_g",
)
REQUIRED_FIELDS = ("part_number",)

CANONICAL_INTERFACES = ("IO-Link", "PROFINET", "EtherCAT", "Modbus RTU", "CANopen", "4-20 mA")
CANONICAL_CERTS = ("CE", "UL", "cULus", "RoHS", "UKCA")

# Fields the agent may constrain on (whitelist, Section 7.8)
AGENT_CONSTRAINT_FIELDS = (
    "supply_voltage_min_v",
    "supply_voltage_max_v",
    "rated_current_a",
    "power_w",
    "operating_temp_min_c",
    "operating_temp_max_c",
    "ip_rating",
    "certifications",
    "interfaces",
    "weight_g",
    "category",
    "manufacturer",
)

_IP_RE = re.compile(r"^IP([0-6])([0-9])(K?)$")


def ip_rank(ip: str | None) -> tuple[int, int] | None:
    """Ordering key for IP ratings; 'K' (high-pressure/steam) ranks above 9."""
    if not ip:
        return None
    m = _IP_RE.match(ip)
    if not m:
        return None
    return int(m.group(1)), 10 if m.group(3) else int(m.group(2))


def ip_at_least(candidate: str | None, original: str | None) -> bool:
    o = ip_rank(original)
    if o is None:
        return True
    c = ip_rank(candidate)
    return c is not None and c >= o


def ranges_overlap(a_lo: Any, a_hi: Any, b_lo: Any, b_hi: Any) -> bool:
    if None in (a_lo, a_hi, b_lo, b_hi):
        return False
    return bool(a_lo <= b_hi and b_lo <= a_hi)


def is_candidate_for(orig: dict[str, Any], cand: dict[str, Any]) -> bool:
    """Deterministic substitution rule shared by the agent search and the ground truth."""
    if orig.get("category") != cand.get("category"):
        return False
    if orig.get("part_number") == cand.get("part_number"):
        return False
    if None in (orig.get("operating_temp_min_c"), orig.get("operating_temp_max_c")):
        return False
    if cand.get("operating_temp_min_c") is None or cand.get("operating_temp_max_c") is None:
        return False
    if not (
        cand["operating_temp_min_c"] <= orig["operating_temp_min_c"]
        and cand["operating_temp_max_c"] >= orig["operating_temp_max_c"]
    ):
        return False
    if not ranges_overlap(
        orig.get("supply_voltage_min_v"),
        orig.get("supply_voltage_max_v"),
        cand.get("supply_voltage_min_v"),
        cand.get("supply_voltage_max_v"),
    ):
        return False
    return ip_at_least(cand.get("ip_rating"), orig.get("ip_rating"))
