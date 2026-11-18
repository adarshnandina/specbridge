"""Extraction evaluation suite (registered with the eval runner)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from specbridge.db.models import Document
from specbridge.db.session import session_scope
from specbridge.eval.datasets import DATASET_DIR, read_jsonl
from specbridge.eval.metrics import latency_summary
from specbridge.eval.runner import SuiteContext, SuiteOutput, register_suite
from specbridge.eval.stats import mean, proportion
from specbridge.extraction.extractor import load_document_pages, run_extraction
from specbridge.extraction.fields import ALL_FIELDS, DIM_FIELD, LIST_FIELDS, NUMERIC_FIELDS
from specbridge.extraction.validators import errors


def values_match(field: str, pred: Any, gt: Any) -> bool:
    empty: tuple[Any, ...] = (None, [], "")
    if pred in empty and gt in empty:
        return True
    if pred in empty or gt in empty:
        return False
    if field in NUMERIC_FIELDS:
        try:
            p, g = float(pred), float(gt)
        except (TypeError, ValueError):
            return False
        return abs(p - g) < 1e-9 if g == 0 else abs(p - g) <= 0.01 * abs(g)
    if field == DIM_FIELD:
        return len(pred) == len(gt) and all(
            abs(float(a) - float(b)) <= 0.01 * max(abs(float(b)), 1e-9)
            for a, b in zip(pred, gt, strict=True)
        )
    if field in LIST_FIELDS:
        return {str(x).strip().lower() for x in pred} == {str(x).strip().lower() for x in gt}
    return " ".join(str(pred).lower().split()) == " ".join(str(gt).lower().split())


def score_document(pred: dict[str, Any], gt: dict[str, Any]) -> dict[str, dict[str, bool | None]]:
    """Per field: correct flag plus tp/fp/fn contributions."""
    out: dict[str, dict[str, bool | None]] = {}
    for f in ALL_FIELDS:
        p, g = pred.get(f), gt.get(f)
        ok = values_match(f, p, g)
        p_set, g_set = p not in (None, [], ""), g not in (None, [], "")
        out[f] = {
            "correct": ok,
            "tp": ok and p_set and g_set,
            "fp": p_set and not ok,
            "fn": g_set and not ok,
        }
    return out


def _prf(tp: int, fp: int, fn: int) -> dict[str, Any]:
    p = proportion(tp, tp + fp)
    r = proportion(tp, tp + fn)
    f1 = (
        2 * p["value"] * r["value"] / (p["value"] + r["value"])
        if p["value"] and r["value"]
        else 0.0
    )
    return {"precision": p, "recall": r, "f1": {"value": f1, "n": tp + fp + fn}}


def aggregate_extraction(items: list[dict[str, Any]]) -> dict[str, Any]:
    tp = sum(i["tp"] for i in items)
    fp = sum(i["fp"] for i in items)
    fn = sum(i["fn"] for i in items)
    per_field: dict[str, Any] = {}
    for f in ALL_FIELDS:
        ftp = sum(1 for i in items if i["fields"][f]["tp"])
        ffp = sum(1 for i in items if i["fields"][f]["fp"])
        ffn = sum(1 for i in items if i["fields"][f]["fn"])
        per_field[f] = _prf(ftp, ffp, ffn)
    validated = [i for i in items if i["status"] == "validated"]
    pred_fields = sum(i["pred_fields"] for i in items)
    ev_bad = sum(i["evidence_errors"] for i in items)
    v_fields = sum(i["pred_fields"] for i in validated)
    v_wrong = sum(i["fp"] for i in validated)
    return {
        "micro": _prf(tp, fp, fn),
        "micro_f1": {"value": _prf(tp, fp, fn)["f1"]["value"], "n": tp + fp + fn},
        "per_field": per_field,
        "evidence_validity": proportion(pred_fields - ev_bad, pred_fields),
        "auto_validated_rate": proportion(len(validated), len(items)),
        "needs_review_rate": proportion(len(items) - len(validated), len(items)),
        "validated_doc_precision": proportion(
            sum(1 for i in validated if i["fp"] == 0 and i["fn"] == 0), len(validated)
        ),
        "validated_field_precision": proportion(v_fields - v_wrong, v_fields),
        "attempts_mean": {"value": mean([float(i["attempts"]) for i in items]), "n": len(items)},
        "n_documents": len(items),
    }


def _run_dataset(
    ctx: SuiteContext, records: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    assert ctx.llm is not None
    ec = ctx.cfg.extraction
    items: list[dict[str, Any]] = []
    calls_all: list[dict[str, Any]] = []
    with session_scope() as db:
        for rec in records:
            doc = db.scalar(select(Document).where(Document.doc_key == rec["doc_key"]))
            if doc is None:
                continue
            if ctx.llm.session_cost > ctx.max_cost:
                break
            pages, tables = load_document_pages(db, doc)
            calls0 = len(ctx.llm.session_calls)
            out = run_extraction(
                ctx.llm, pages, tables, retry=bool(ec.get("retry", True)), model=ec.get("model")
            )
            calls = ctx.llm.session_calls[calls0:]
            calls_all += calls
            sc = score_document(out.normalized.data, rec["spec"])
            errs = errors(out.issues)
            ev_err = sum(1 for i in errs if i.rule.startswith("evidence"))
            items.append(
                {
                    "doc_key": rec["doc_key"],
                    "status": "pending_review" if errs else "validated",
                    "attempts": out.attempts,
                    "fields": sc,
                    "tp": sum(bool(v["tp"]) for v in sc.values()),
                    "fp": sum(bool(v["fp"]) for v in sc.values()),
                    "fn": sum(bool(v["fn"]) for v in sc.values()),
                    "pred_fields": sum(
                        1 for f in ALL_FIELDS if out.normalized.data.get(f) not in (None, [])
                    ),
                    "evidence_errors": ev_err,
                    "errors": [f"{i.field}:{i.rule}" for i in errs],
                    "wrong_fields": [f for f, v in sc.items() if not v["correct"]],
                    "cost_usd": sum(c["cost_usd"] for c in calls),
                    "latency_ms": sum(c["latency_ms"] for c in calls if not c["cache_hit"]),
                    "cache_hit": any(c["cache_hit"] for c in calls),
                }
            )
    return items, calls_all


def run_extraction_suite(ctx: SuiteContext) -> SuiteOutput:
    assert ctx.llm is not None
    ec = ctx.cfg.extraction
    cost0 = ctx.llm.session_cost
    syn = [
        r
        for r in read_jsonl(DATASET_DIR / "extraction_synthetic.jsonl")
        if ctx.split in ("all", r["split"])
    ]
    items, calls = _run_dataset(ctx, syn)
    aggregates: dict[str, Any] = {"extraction": aggregate_extraction(items)}
    all_items = [{**i, "dataset": "synthetic"} for i in items]
    notes = []
    if ctx.provider_name == "fake":
        notes.append(
            "fake provider: rule-based regex extractor - pipeline check only, NOT a model "
            "quality result"
        )
    if ec.get("include_real", True):
        real = [
            r
            for r in read_jsonl(DATASET_DIR / "extraction_real.jsonl")
            if ctx.split in ("all", r["split"])
        ]
        r_items, r_calls = _run_dataset(ctx, real)
        calls += r_calls
        if r_items:
            aggregates["extraction_real"] = aggregate_extraction(r_items)
            all_items += [{**i, "dataset": "real"} for i in r_items]
            notes.append(
                "extraction_real: labels are PROVISIONAL (verified_by_human=false); "
                "metrics on them are provisional"
            )
    cost = ctx.llm.session_cost - cost0
    nd = len(items) or 1
    ops = {
        "latency_ms": latency_summary(i["latency_ms"] for i in items if not i["cache_hit"]),
        "cost_usd": cost,
        "cost_per_document": cost / nd,
        "llm_calls": len(calls),
        "input_tokens": sum(c["input_tokens"] for c in calls),
        "output_tokens": sum(c["output_tokens"] for c in calls),
    }
    model = ec.get("model") or ctx.llm.settings.model_for("extraction")
    return SuiteOutput(
        all_items,
        aggregates,
        ops,
        cost,
        {"extraction": model},
        sorted({c["prompt_version"] for c in calls if c["prompt_version"]}),
        notes,
    )


register_suite("extraction", run_extraction_suite)
