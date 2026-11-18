"""Abstention-threshold calibration (experiment 7). No LLM calls: uses the retrieval score gate.

For every dev QA item we record the best vector similarity of the retrieved chunks, then sweep the
cut-off t ("abstain without calling the LLM if score < t") and report precision/recall of that
pre-filter on the questions that should be abstained on, and the share of ANSWERABLE questions it
would wrongly block.
"""

from __future__ import annotations

from typing import Any

from specbridge.db.session import session_scope
from specbridge.eval.datasets import load_qa
from specbridge.eval.metrics import latency_summary
from specbridge.eval.runner import SuiteContext, SuiteOutput, _check_index, register_suite
from specbridge.eval.stats import proportion
from specbridge.ingestion.embeddings import get_embedder
from specbridge.retrieval.service import retrieve

MAX_OVER_ABSTENTION = 0.05


def sweep(
    scores: list[tuple[float, bool]], lo: float = 0.30, hi: float = 0.90, step: float = 0.01
) -> list[dict[str, Any]]:
    """scores: (top_vector_score, expect_abstain). Abstain iff score < t."""
    pos = [s for s, e in scores if e]
    neg = [s for s, e in scores if not e]
    out = []
    n = int(round((hi - lo) / step))
    for i in range(n + 1):
        t = round(lo + i * step, 4)
        tp = sum(1 for s in pos if s < t)
        fp = sum(1 for s in neg if s < t)
        out.append(
            {
                "threshold": t,
                "abstained": tp + fp,
                "precision": proportion(tp, tp + fp),
                "recall": proportion(tp, len(pos)),
                "over_abstention": proportion(fp, len(neg)),
            }
        )
    return out


def recommend(curve: list[dict[str, Any]], max_over: float = MAX_OVER_ABSTENTION) -> dict[str, Any]:
    """Largest threshold whose over-abstention on answerable questions stays <= max_over."""
    ok = [
        c
        for c in curve
        if c["over_abstention"]["value"] is not None and c["over_abstention"]["value"] <= max_over
    ]
    best = max(ok, key=lambda c: c["threshold"]) if ok else curve[0]
    return best


def run_calibration(ctx: SuiteContext) -> SuiteOutput:
    index = ctx.cfg.index_name or ctx.settings.default_index
    _check_index(index)
    emb = ctx.embedder or get_embedder()
    emb.embed_query("warm up")
    rc = ctx.cfg.retrieval
    items = load_qa(split=ctx.split)
    rows: list[dict[str, Any]] = []
    lat: list[float] = []
    with session_scope() as db:
        for q in items:
            r = retrieve(
                db,
                q.question,
                index=index,
                mode=rc.get("mode"),
                top_k=rc.get("top_k"),
                rerank=rc.get("rerank"),
                embedder=emb,
            )
            lat.append(r.latency_ms)
            rows.append(
                {
                    "id": q.id,
                    "type": q.type,
                    "expect_abstain": q.expect_abstain,
                    "top_vector_score": r.top_vector_score,
                }
            )
    curve = sweep([(r["top_vector_score"], r["expect_abstain"]) for r in rows])
    rec = recommend(curve)
    ans = [r["top_vector_score"] for r in rows if not r["expect_abstain"]]
    una = [r["top_vector_score"] for r in rows if r["expect_abstain"]]
    agg = {
        "calibration": {
            "curve": curve,
            "recommended_threshold": rec["threshold"],
            "recommended_at": {k: rec[k] for k in ("precision", "recall", "over_abstention")},
            "criterion": f"largest threshold with over-abstention on answerable questions <= "
            f"{MAX_OVER_ABSTENTION:.0%}",
            "score_summary": {
                "answerable_mean": sum(ans) / max(len(ans), 1),
                "unanswerable_mean": sum(una) / max(len(una), 1),
                "n_answerable": len(ans),
                "n_unanswerable": len(una),
            },
        }
    }
    return SuiteOutput(
        rows,
        agg,
        {"retrieval_latency_ms": latency_summary(lat)},
        0.0,
        {},
        [],
        [
            "calibrated on the retrieval score only; the LLM's own answerable flag is "
            "a second, independent abstention mechanism"
        ],
    )


register_suite("calibration", run_calibration)
