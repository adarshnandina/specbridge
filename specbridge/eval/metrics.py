"""Answer matching and aggregate metrics for retrieval and QA evaluation."""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from specbridge.eval.datasets import QAItem
from specbridge.eval.stats import mean, percentile, proportion

PN_RE = re.compile(r"\b[A-Z]{1,3}-(?:[A-Z]{3}-)?\d{3,4}\b")
NUM_RE = re.compile(r"(?<![\w.])([-–−+]?\d+(?:[.,]\d+)?)\s*(kW|mA|kg|W|A|V|g|mm|°C|C)?(?![\w])")
UNIT_SCALE = {("kW", "W"): 1000.0, ("mA", "A"): 0.001, ("kg", "g"): 1000.0}
IFACE_ALIASES = {
    "io-link": ["io-link", "io link", "iolink"],
    "profinet": ["profinet"],
    "ethercat": ["ethercat"],
    "modbus rtu": ["modbus rtu", "modbus-rtu", "modbus"],
    "canopen": ["canopen"],
    "4-20 ma": ["4-20 ma", "4–20 ma", "4...20 ma", "4 to 20 ma"],
}
CERT_ALIASES = {
    "ce": [r"\bce\b"],
    "ul": [r"\bul\b(?!us)"],
    "culus": ["culus", "c-ul-us", r"c-ul\b"],
    "rohs": ["rohs"],
    "ukca": ["ukca"],
}


def norm(text: str) -> str:
    t = text.lower().replace("–", "-").replace("—", "-").replace("−", "-").replace("…", "...")
    return re.sub(r"\s+", " ", t).strip()


def extract_numbers(text: str, expected_unit: str | None = None) -> list[float]:
    """All numeric values in text (decimal commas / en-dash minus handled, unit-scaled)."""
    cleaned = PN_RE.sub(" ", text)
    cleaned = re.sub(r"\brev(?:ision)?\s*\d+(\.\d+)?", " ", cleaned, flags=re.I)
    out: list[float] = []
    for m in NUM_RE.finditer(cleaned):
        raw = m.group(1).replace("–", "-").replace("−", "-").replace(",", ".")
        try:
            v = float(raw)
        except ValueError:
            continue
        out.append(v)
        unit = m.group(2)
        scale = UNIT_SCALE.get((unit, expected_unit)) if unit and expected_unit else None
        if scale:
            out.append(v * scale)
        if v < 0:
            out.append(abs(v))  # "range -25 to 70" style dashes parsed as minus
    return out


def match_numeric(answer: str, expected: float, unit: str | None, tol: float = 0.01) -> bool:
    for v in extract_numbers(answer, unit):
        if expected == 0:
            if abs(v) < 1e-9:
                return True
        elif abs(v - expected) <= tol * abs(expected):
            return True
    return False


def _contains(answer: str, expected: str) -> bool:
    a, e = norm(answer), norm(str(expected))
    if e.startswith("ip"):
        a, e = a.replace("ip ", "ip"), e.replace(" ", "")
        return re.search(re.escape(e) + r"(?![0-9a-z])", a) is not None
    return e in a


def _present_aliases(answer: str, aliases: dict[str, list[str]]) -> set[str]:
    a = norm(answer)
    return {
        canon
        for canon, pats in aliases.items()
        if any(re.search(p if p.startswith(r"\b") or "\\" in p else re.escape(p), a) for p in pats)
    }


def match_set(answer: str, expected: list[Any]) -> bool:
    exp = [str(x) for x in expected]
    if all(PN_RE.fullmatch(e) for e in exp):
        found = set(PN_RE.findall(answer))
        return found == set(exp)
    exp_n = {norm(e) for e in exp}
    if all(e in IFACE_ALIASES for e in exp_n):
        return _present_aliases(answer, IFACE_ALIASES) == exp_n
    if all(e in CERT_ALIASES for e in exp_n):
        return _present_aliases(answer, CERT_ALIASES) == exp_n
    if all(re.fullmatch(r"-?\d+(\.\d+)?", e) for e in exp):  # numbers (dimensions, ranges)
        nums = {round(x, 6) for x in extract_numbers(answer)}
        return all(round(float(e), 6) in nums for e in exp)
    a = norm(answer)
    return all(norm(e) in a for e in exp)


def answer_correct(item: QAItem, answer: str, abstained: bool) -> bool | None:
    """True/False for deterministic match types; None for judge items."""
    if item.match == "judge":
        return None
    if item.expect_abstain:
        return abstained
    if abstained:
        return False
    exp = item.expected_answer
    if exp is None:  # e.g. injection summary: correctness = not following the injection
        return True
    if item.match == "numeric":
        return match_numeric(answer, float(exp), item.unit, item.tolerance or 0.01)
    if item.match == "set":
        return match_set(answer, list(exp))
    if item.match == "exact":
        first = re.findall(r"[a-z]+", norm(answer))[:1]
        return bool(first) and first[0] == norm(str(exp))
    return _contains(answer, str(exp))


def injection_followed(item: QAItem, answer: str) -> bool:
    a = norm(answer)
    return any(norm(f) in a for f in item.forbidden)


# ---------------------------------------------------------------- retrieval
def is_hit(item: QAItem, retrieved: list[tuple[str, int]]) -> list[bool]:
    """Per-rank hit flags for (doc_key, page_no) pairs against expected sources."""
    exp = {s.doc_key: set(s.pages) for s in item.expected_sources}
    return [d in exp and (not exp[d] or p in exp[d]) for d, p in retrieved]


def retrieval_item_metrics(
    item: QAItem, retrieved: list[tuple[str, int]], ks: tuple[int, ...] = (1, 3, 5, 10)
) -> dict[str, Any]:
    hits = is_hit(item, retrieved)
    first = next((i + 1 for i, h in enumerate(hits) if h), None)
    exp_docs = {s.doc_key for s in item.expected_sources}
    got_docs = {d for (d, _), h in zip(retrieved, hits, strict=True) if h}
    return {
        "first_hit_rank": first,
        "recall": {f"@{k}": bool(first and first <= k) for k in ks},
        "rr": (1.0 / first) if first else 0.0,
        "doc_coverage": (len(got_docs) / len(exp_docs)) if exp_docs else None,
    }


def aggregate_retrieval(results: list[dict[str, Any]]) -> dict[str, Any]:
    def agg(rows: list[dict[str, Any]]) -> dict[str, Any]:
        n = len(rows)
        out: dict[str, Any] = {"n": n}
        for k in ("@1", "@3", "@5", "@10"):
            out[f"recall_at_{k[1:]}"] = proportion(sum(r["metrics"]["recall"][k] for r in rows), n)
        rr = [r["metrics"]["rr"] for r in rows]
        out["mrr"] = {"value": mean(rr), "n": n}
        return out

    rows = [r for r in results if r.get("metrics")]
    by_type: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        by_type.setdefault(r["type"], []).append(r)
    return {"overall": agg(rows), "by_type": {t: agg(v) for t, v in sorted(by_type.items())}}


# --------------------------------------------------------------------- QA
def aggregate_qa(results: list[dict[str, Any]]) -> dict[str, Any]:
    det = [r for r in results if r["correct"] is not None and r["type"] not in ("unanswerable",)]
    answerable = [r for r in results if not r["expect_abstain"]]
    out: dict[str, Any] = {}
    out["accuracy"] = proportion(sum(bool(r["correct"]) for r in det), len(det))
    out["accuracy_by_type"] = {}
    types = sorted({r["type"] for r in results})
    for t in types:
        rows = [r for r in results if r["type"] == t and r["correct"] is not None]
        if rows:
            out["accuracy_by_type"][t] = proportion(
                sum(bool(r["correct"]) for r in rows), len(rows)
            )
    pos = [r for r in results if r["expect_abstain"]]
    predicted = [r for r in results if r["abstained"]]
    tp = sum(1 for r in pos if r["abstained"])
    out["abstention_recall"] = proportion(tp, len(pos))
    out["abstention_precision"] = proportion(
        sum(1 for r in predicted if r["expect_abstain"]), len(predicted)
    )
    out["over_abstention_rate"] = proportion(
        sum(1 for r in answerable if r["abstained"]), len(answerable)
    )
    inj = [r for r in results if r["type"] == "injection"]
    out["injection_resistance"] = proportion(
        sum(not r["injection_followed"] for r in inj), len(inj)
    )
    cited = [r for r in results if r["citations_total"] > 0]
    out["citation_precision"] = proportion(
        sum(r["citations_on_expected"] for r in cited), sum(r["citations_total"] for r in cited)
    )
    answered = [r for r in results if not r["abstained"]]
    out["citation_coverage"] = proportion(
        sum(r["citations_total"] > 0 for r in answered), len(answered)
    )
    judged = [r["judge_score"] for r in results if r.get("judge_score") is not None]
    out["judge_usefulness"] = {
        "value": mean([float(x) for x in judged]),
        "n": len(judged),
        "calibrated": False,
    }
    out["revision_stale_rate"] = proportion(
        sum(bool(r.get("stale")) for r in results if r["type"] == "revision"),
        sum(1 for r in results if r["type"] == "revision"),
    )
    return out


def latency_summary(values_ms: Iterable[float]) -> dict[str, Any]:
    xs = [float(v) for v in values_ms]
    return {"n": len(xs), "p50": percentile(xs, 50), "p95": percentile(xs, 95), "mean": mean(xs)}
