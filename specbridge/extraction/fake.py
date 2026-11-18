"""Rule-based stand-in for the extraction LLM (FakeProvider): a regex baseline, pipeline check only."""

from __future__ import annotations

import re
from typing import Any

from specbridge.extraction import units as U
from specbridge.llm.base import LLMRequest
from specbridge.llm.fake_provider import FakeProvider

PAGE_RE = re.compile(r'<page number="(\d+)">\n(.*?)\n</page>', re.S)
LABEL_RULES: list[tuple[str, str]] = [
    ("product group", "category"),
    ("voltage", "supply"),
    ("current", "rated_current_a"),
    ("power", "power_w"),
    ("temperature", "temp"),
    ("protection", "ip_rating"),
    ("dimension", "dimensions_mm"),
    ("weight", "weight_g"),
    ("interface", "interfaces"),
    ("approval", "certifications"),
]
UNIT_RE = re.compile(r"(?<![A-Za-z])(mA|kW|kg|mV|kV|W|A|V|g|mm)(?![A-Za-z])")


def _fv(value: Any, unit: str | None, page: int, quote: str) -> dict[str, Any]:
    return {"value": value, "unit": unit, "page": page, "quote": quote}


def extract_from_pages(pages: dict[int, str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for n, text in pages.items():
        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
        for i, line in enumerate(lines):
            m = re.match(r"^(.*?) · (\S+) · Revision (\S+) ·", line)
            if m and n == min(pages):
                out.setdefault("manufacturer", _fv(m.group(1), None, n, line.split(" ·")[0]))
            m = re.search(r"Part number:\s*(\S+)\s*\|\s*Revision\s*(\d+(?:\.\d+)*)", line)
            if m:
                out.setdefault(
                    "part_number", _fv(m.group(1), None, n, f"Part number: {m.group(1)}")
                )
                out.setdefault(
                    "datasheet_revision", _fv(m.group(2), None, n, f"Revision {m.group(2)}")
                )
                if i > 0:
                    out.setdefault("product_name", _fv(lines[i - 1], None, n, lines[i - 1]))
                continue
            low = line.lower().lstrip("•- ").strip()
            if len(line) > 70 or low.startswith(("note", "installation", "technical data")):
                continue
            rule = next((k for kw, k in LABEL_RULES if kw in low.split(":")[0]), None)
            if rule is None:
                continue
            label = re.sub(r"[¹²³]", "", line.lstrip("•- ").split(":")[0]).strip()
            if ":" in line:
                value = line.split(":", 1)[1].strip()
                quote = line.lstrip("• ").strip()
            elif i + 1 < len(lines):
                value = lines[i + 1]
                quote = f"{line} {value}"
            else:
                continue
            hdr = re.search(r"\[([^\]]+)\]", label)
            unit = hdr.group(1) if hdr else None
            _assign(out, rule, value, unit, n, quote)
    return out


def _assign(
    out: dict[str, Any], rule: str, value: str, hdr_unit: str | None, page: int, quote: str
) -> None:
    um = UNIT_RE.search(value)
    unit = hdr_unit or (um.group(1) if um else None)
    if rule == "category":
        out.setdefault("category", _fv(value, None, page, quote))
    elif rule == "supply":
        rng = U.parse_range(value)
        if rng and "supply_voltage_min_v" not in out:
            out["supply_voltage_min_v"] = _fv(rng[0], "V", page, quote)
            out["supply_voltage_max_v"] = _fv(rng[1], "V", page, quote)
    elif rule == "temp":
        rng = U.parse_range(value)
        if rng and "operating_temp_min_c" not in out:
            out["operating_temp_min_c"] = _fv(rng[0], "°C", page, quote)
            out["operating_temp_max_c"] = _fv(rng[1], "°C", page, quote)
    elif rule == "ip_rating":
        out.setdefault("ip_rating", _fv(value, None, page, quote))
    elif rule == "dimensions_mm":
        nums = U.numbers_in(value)
        if len(nums) == 3:
            out.setdefault("dimensions_mm", _fv(nums, "mm", page, quote))
    elif rule in ("interfaces", "certifications"):
        items = [x.strip() for x in re.split(r",", value) if x.strip()]
        out.setdefault(rule, _fv(items, None, page, quote))
    else:  # single numbers
        nums = U.numbers_in(value)
        if nums and rule not in out:
            u = unit
            if rule == "rated_current_a" and u in (None, "[A]"):
                u = u or "A"
            out[rule] = _fv(nums[0], u, page, quote)


def extraction_handler(req: LLMRequest) -> dict[str, Any]:
    content = req.messages[-1]["content"]
    pages = {int(n): t for n, t in PAGE_RE.findall(content)}
    return extract_from_pages(pages)


def register_extraction_handlers(fake: FakeProvider) -> FakeProvider:
    fake.register("extraction", extraction_handler)
    return fake
