"""Citation verification: a quote must fuzzy-match its source chunk."""

from __future__ import annotations

import re
from dataclasses import dataclass

from rapidfuzz import fuzz

MIN_QUOTE_CHARS = 3
THRESHOLD = 90.0
_DASHES = str.maketrans({"–": "-", "—": "-", "−": "-", "‐": "-", "‑": "-"})


def normalize(text: str) -> str:
    t = text.translate(_DASHES).replace("…", "...").replace("×", "x").replace(" ", " ")
    t = re.sub(r"[|]", " ", t)
    return re.sub(r"\s+", " ", t).strip().lower()


def quote_matches(quote: str, source_text: str, threshold: float = THRESHOLD) -> bool:
    q, s = normalize(quote), normalize(source_text)
    if len(q) < MIN_QUOTE_CHARS or not s:
        return False
    return float(fuzz.partial_ratio(q, s)) >= threshold


@dataclass
class VerifiedCitation:
    source_id: str
    quote: str
    valid: bool
    reason: str = ""


def verify_citations(
    citations: list[tuple[str, str]], sources: dict[str, str]
) -> list[VerifiedCitation]:
    out = []
    for sid, quote in citations:
        if sid not in sources:
            out.append(VerifiedCitation(sid, quote, False, "unknown_source"))
        elif quote_matches(quote, sources[sid]):
            out.append(VerifiedCitation(sid, quote, True))
        else:
            out.append(VerifiedCitation(sid, quote, False, "quote_not_in_source"))
    return out
