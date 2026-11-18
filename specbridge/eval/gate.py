"""Regression gate: compare a candidate run with the baseline using eval/thresholds.yaml."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from specbridge.eval.compare import load_run
from specbridge.eval.datasets import relevant_datasets
from specbridge.eval.runner import RESULTS_DIR, latest_run

THRESHOLDS = Path("eval/thresholds.yaml")


@dataclass
class Check:
    name: str
    baseline: float | None
    candidate: float | None
    limit: str
    ok: bool
    detail: str = ""


def _get(run: dict[str, Any], path: list[str]) -> float | None:
    cur: Any = run
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return None
        cur = cur[p]
    if isinstance(cur, dict):
        cur = cur.get("value")
    return None if cur is None else float(cur)


def _drop_check(
    name: str, base: dict[str, Any], cand: dict[str, Any], path: list[str], max_drop: float
) -> Check | None:
    b, c = _get(base, path), _get(cand, path)
    if b is None or c is None:
        return None
    drop = b - c
    return Check(name, b, c, f"drop <= {max_drop}", drop <= max_drop + 1e-12, f"drop {drop:+.4f}")


def _pct_check(
    name: str,
    base: dict[str, Any],
    cand: dict[str, Any],
    path: list[str],
    max_pct: float,
    min_abs: float = 0.0,
) -> Check | None:
    b, c = _get(base, path), _get(cand, path)
    if b is None or c is None or b <= 0:
        return None
    pct = (c - b) / b * 100
    ok = pct <= max_pct or (c - b) <= min_abs
    return Check(name, b, c, f"increase <= {max_pct}%", ok, f"{pct:+.1f}% ({c - b:+.1f})")


def evaluate(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    thresholds: dict[str, Any],
    suites: list[str] | None = None,
) -> list[Check]:
    def on(s: str) -> bool:
        return suites is None or s in suites

    checks: list[Check | None] = []
    agg_b, agg_c = "aggregates", "aggregates"
    t = thresholds
    if on("retrieval") and "retrieval" in t:
        p = [agg_b, "retrieval", "overall"]
        checks += [
            _drop_check(
                "retrieval.recall_at_5",
                baseline,
                candidate,
                [*p, "recall_at_5"],
                t["retrieval"]["recall_at_5_drop"],
            ),
            _drop_check(
                "retrieval.mrr", baseline, candidate, [*p, "mrr"], t["retrieval"]["mrr_drop"]
            ),
        ]
        checks.append(
            _pct_check(
                "ops.retrieval.p95_latency_ms",
                baseline,
                candidate,
                ["ops", "retrieval", "retrieval_latency_ms", "p95"],
                t["ops"]["p95_latency_increase_pct"],
                t.get("ops_noise_floor", {}).get("p95_latency_min_abs_ms", 0),
            )
        )
    if on("qa") and "qa" in t:
        p = [agg_b, "qa"]
        checks += [
            _drop_check(
                "qa.accuracy", baseline, candidate, [*p, "accuracy"], t["qa"]["accuracy_drop"]
            ),
            _drop_check(
                "qa.citation_precision",
                baseline,
                candidate,
                [*p, "citation_precision"],
                t["qa"]["citation_precision_drop"],
            ),
            _drop_check(
                "qa.abstention_recall",
                baseline,
                candidate,
                [*p, "abstention_recall"],
                t["qa"]["abstention_recall_drop"],
            ),
            _pct_check(
                "ops.qa.p95_total_latency_ms",
                baseline,
                candidate,
                ["ops", "qa", "total_latency_ms", "p95"],
                t["ops"]["p95_latency_increase_pct"],
                t.get("ops_noise_floor", {}).get("p95_latency_min_abs_ms", 0),
            ),
            _pct_check(
                "ops.qa.cost_per_100_queries",
                baseline,
                candidate,
                ["ops", "qa", "cost_per_100_queries"],
                t["ops"]["cost_per_100_increase_pct"],
            ),
        ]
    if on("extraction") and "extraction" in t:
        checks.append(
            _drop_check(
                "extraction.micro_f1",
                baseline,
                candidate,
                [agg_b, "extraction", "micro_f1"],
                t["extraction"]["micro_f1_drop"],
            )
        )
    if on("agent") and t.get("agent", {}).get("safety_scenarios_must_pass"):
        a = candidate.get("aggregates", {}).get("agent")
        if a is not None:
            checks.append(
                Check(
                    "agent.safety_scenarios",
                    1.0,
                    1.0 if a["safety_all_pass"] else 0.0,
                    "all safety scenarios pass",
                    bool(a["safety_all_pass"]),
                    "; ".join(f["id"] for f in a["failures"] if f["safety"]),
                )
            )
    del agg_c
    return [c for c in checks if c is not None]


def run_gate(
    baseline_path: str | Path,
    candidate: str,
    thresholds_path: Path = THRESHOLDS,
    suites: list[str] | None = None,
    tag: str | None = None,
    allow_dataset_change: bool = False,
) -> tuple[bool, str]:
    base = load_run(baseline_path)
    cand_path = latest_run(RESULTS_DIR, tag) if candidate == "latest" else Path(candidate)
    cand = load_run(cand_path)
    thresholds = yaml.safe_load(Path(thresholds_path).read_text())
    problems: list[str] = []
    if base["split"] != cand["split"]:
        problems.append(f"split mismatch: baseline={base['split']} candidate={cand['split']}")
    gated = suites or list(cand.get("suites", []))
    keys = relevant_datasets(gated) or set(base.get("datasets", {})) | set(cand.get("datasets", {}))
    bd, cd = base.get("datasets", {}), cand.get("datasets", {})
    diff = sorted(k for k in keys if bd.get(k) != cd.get(k))
    if not allow_dataset_change and diff:
        problems.append(
            f"dataset hashes differ ({', '.join(diff)}): runs are not comparable; "
            "re-baseline or pass --allow-dataset-change"
        )
    checks = evaluate(base, cand, thresholds, suites)
    lines = [
        f"# Gate: baseline `{base['run_id']}` vs candidate `{cand['run_id']}`",
        "",
        "| check | baseline | candidate | limit | result | detail |",
        "|---|---|---|---|---|---|",
    ]
    for c in checks:
        lines.append(
            f"| {c.name} | {c.baseline:.4f} | {c.candidate:.4f} | {c.limit} | "
            f"{'PASS' if c.ok else '**FAIL**'} | {c.detail} |"
        )
    if not checks:
        problems.append("no comparable metrics found between the two runs")
    for p in problems:
        lines.append(f"\n**PROBLEM:** {p}")
    ok = bool(checks) and all(c.ok for c in checks) and not problems
    lines.append(f"\n**Gate {'PASSED' if ok else 'FAILED'}**")
    return ok, "\n".join(lines)
