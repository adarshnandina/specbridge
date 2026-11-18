"""Unit normalisation: pint conversions, decimal commas, en-dash ranges, IP, alias maps."""

from __future__ import annotations

import re
from typing import Any

import pint

ureg = pint.UnitRegistry()
_DASH = "-–−‐‑—"
_SIGN_CLASS = r"[+\-–−‐‑—]"
NUM = r"\d+(?:[.,]\d+)*"
_NUM_RE = re.compile(rf"({_SIGN_CLASS}?)\s?({NUM})")

UNIT_TARGETS = {
    "supply_voltage_min_v": "V",
    "supply_voltage_max_v": "V",
    "rated_current_a": "A",
    "power_w": "W",
    "operating_temp_min_c": "degC",
    "operating_temp_max_c": "degC",
    "weight_g": "g",
}

INTERFACE_ALIASES = {
    "IO-Link": [r"io[\s-]?link"],
    "PROFINET": [r"profinet"],
    "EtherCAT": [r"ethercat"],
    "Modbus RTU": [r"modbus"],
    "CANopen": [r"canopen"],
    "4-20 mA": [r"4\s*(?:-|–|—|to|\.\.\.?)\s*20\s*ma"],
}
CERT_ALIASES = {
    "CE": [r"^ce$", r"^ce[\s-]"],
    "UL": [r"^ul(?!us)\b(?:\s*listed|\s*508|\s*recognized|$)", r"^ul\s"],
    "cULus": [r"^c-?ul-?us$", r"^culus$"],
    "RoHS": [r"rohs"],
    "UKCA": [r"ukca"],
}
CATEGORY_ALIASES = {
    "sensor": ["sensor", "proximity", "transmitter", "switch"],
    "drive": ["drive", "inverter", "servo", "stepper", "converter"],
    "io_module": ["i/o", "io module", "io_module", "input/output", "remote io"],
    "power_supply": ["power supply", "power_supply", "psu", "supply unit"],
}


def parse_number(s: str) -> float | None:
    """'1,5' -> 1.5; '1.234,5' -> 1234.5; '3,000' -> 3000 (thousands); '1e3' not supported."""
    t = s.strip().replace(" ", "")
    if not re.fullmatch(NUM, t):
        return None
    if "," in t and "." in t:
        if t.rfind(",") > t.rfind("."):
            t = t.replace(".", "").replace(",", ".")
        else:
            t = t.replace(",", "")
    elif "," in t:
        head, _, tail = t.rpartition(",")
        if t.count(",") > 1 or (len(tail) == 3 and 1 <= len(head) <= 3 and head != "0"):
            t = t.replace(",", "")
        else:
            t = t.replace(",", ".")
    return float(t)


def numbers_in(text: str) -> list[float]:
    """All numbers in text honouring signs (a dash is a sign only if not preceded by alnum)."""
    out: list[float] = []
    for m in _NUM_RE.finditer(text):
        sign, digits = m.group(1), m.group(2)
        v = parse_number(digits)
        if v is None:
            continue
        start = m.start()
        prev = text[:start].rstrip()
        prev_ch = prev[-1] if prev else ""
        is_sign = bool(sign) and (
            sign == "+" or not (prev_ch and (prev_ch.isalnum() or prev_ch in ")%°"))
        )
        if sign and sign in _DASH and is_sign:
            v = -v
        out.append(v)
    return out


def parse_range(text: str) -> tuple[float, float] | None:
    """'-40 °C … +85 °C', '–40 to 85 °C', '24 V DC (18–30 V)', '18-30 V DC' -> (lo, hi)."""
    t = text
    paren = re.search(rf"\(([^)]*{NUM}[^)]*{NUM}[^)]*)\)", t)
    if paren:
        t = paren.group(1)
    nums = numbers_in(t)
    if len(nums) < 2:
        return None
    return (min(nums[0], nums[1]), max(nums[0], nums[1]))


def clean_unit(unit: str | None) -> str | None:
    if not unit:
        return None
    u = unit.strip()
    u = re.sub(r"\s*(?:DC|AC)\b", "", u, flags=re.I) if u.upper().startswith("V") else u
    u = u.replace("°C", "degC").replace("ºC", "degC").replace("℃", "degC").replace("°F", "degF")
    u = u.replace("Ω", "ohm").replace("µ", "u").replace("μ", "u")
    return u.strip() or None


def convert(value: float, unit: str | None, target: str) -> float | None:
    """Convert value from unit to target using pint; None if the unit is incompatible."""
    u = clean_unit(unit)
    if u is None or u.lower() == target.lower():
        return value
    try:
        if target == "degC":
            return float(ureg.Quantity(value, u).to("degC").magnitude)
        return float(ureg.Quantity(value, u).to(target).magnitude)
    except (pint.errors.PintError, AttributeError, ValueError, TypeError):
        return None


def all_ips(text: str) -> list[str]:
    """Every valid, normalised IP rating mentioned in text."""
    from specbridge.extraction.fields import ip_rank

    found = [
        f"IP{m.group(1)}{m.group(2)}{m.group(3).upper()}"
        for m in re.finditer(r"IP\s*([0-6])\s*([0-9])\s*(K?)", text, flags=re.I)
    ]
    return [f for f in found if ip_rank(f)]


def normalize_ip(text: str) -> str | None:
    """'IP 67' -> 'IP67'; 'IP67/IP69K' -> highest rating."""
    from specbridge.extraction.fields import ip_rank

    found = [
        f"IP{m.group(1)}{m.group(2)}{m.group(3).upper()}"
        for m in re.finditer(r"IP\s*([0-6])\s*([0-9])\s*(K?)", text, flags=re.I)
    ]
    found = [f for f in found if ip_rank(f)]
    if not found:
        return None
    return max(found, key=lambda x: ip_rank(x) or (0, 0))


def _split_items(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"[;,]|\s/\s|\band\b|\n", text) if p.strip()]


def canonical_interfaces(items: Any) -> list[str]:
    parts = _split_items(items) if isinstance(items, str) else [str(i) for i in items]
    out: list[str] = []
    for p in parts:
        canon = next(
            (
                c
                for c, pats in INTERFACE_ALIASES.items()
                if any(re.search(x, p.lower()) for x in pats)
            ),
            None,
        )
        val = canon or p.strip()
        if val and val not in out:
            out.append(val)
    return out


def canonical_certs(items: Any) -> list[str]:
    parts = _split_items(items) if isinstance(items, str) else [str(i) for i in items]
    out: list[str] = []
    for p in parts:
        low = p.lower().strip()
        canon = next(
            (c for c, pats in CERT_ALIASES.items() if any(re.search(x, low) for x in pats)), None
        )
        val = canon or p.strip()
        if val and val not in out:
            out.append(val)
    return out


def canonical_category(text: str) -> str:
    low = text.lower()
    for cat, words in CATEGORY_ALIASES.items():
        if any(w in low for w in words):
            return cat
    return "other"
