"""Compare two eval runs: deltas, intervals and within-noise flags."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from specbridge.eval.stats import noise_flag


def load_run(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        cand = Path("eval_results") / (p.name if p.suffix else p.name + ".json")
        if cand.exists():
            p = cand
    data: dict[str, Any] = json.loads(p.read_text())
    return data


def flatten(agg: dict[str, Any], prefix: str = "") -> dict[str, dict[str, Any]]:
    """Leaf metrics are dicts with a 'value' key."""
    out: dict[str, dict[str, Any]] = {}
    for k, v in agg.items():
        name = f"{prefix}{k}"
        if isinstance(v, dict) and "value" in v:
            out[name] = v
        elif isinstance(v, dict):
            out.update(flatten(v, name + "."))
    return out


def ops_metrics(run: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for suite, ops in run.get("ops", {}).items():
        for k, v in ops.items():
            if isinstance(v, dict) and "p95" in v and v.get("p95") is not None:
                out[f"ops.{suite}.{k}.p50"] = {"value": v["p50"], "n": v["n"]}
                out[f"ops.{suite}.{k}.p95"] = {"value": v["p95"], "n": v["n"]}
            elif k in ("cost_usd", "cost_per_100_queries", "cost_per_document") and v is not None:
                out[f"ops.{suite}.{k}"] = {"value": v, "n": 1}
    return out


def all_metrics(run: dict[str, Any]) -> dict[str, dict[str, Any]]:
    m = flatten(run.get("aggregates", {}))
    m.update(ops_metrics(run))
    return m


def compare_runs(a: dict[str, Any], b: dict[str, Any]) -> str:
    ma, mb = all_metrics(a), all_metrics(b)
    rows = ["| metric | A | B | delta (B-A) | noise |", "|---|---|---|---|---|"]
    for name in sorted(set(ma) & set(mb)):
        if ".by_type." in name or "accuracy_by_type" in name:
            continue
        x, y = ma[name], mb[name]
        if x.get("value") is None or y.get("value") is None:
            continue
        d = y["value"] - x["value"]
        flag = noise_flag(x, y) if "ci" in x and "ci" in y else ""
        rows.append(f"| {name} | {_f(x)} | {_f(y)} | {d:+.4f} | {flag} |")
    head = [
        f"# Compare `{a['run_id']}` (A) vs `{b['run_id']}` (B)",
        "",
        f"- A: split={a['split']} provider={a['provider']} config={json.dumps(a['config'])}",
        f"- B: split={b['split']} provider={b['provider']} config={json.dumps(b['config'])}",
        "- noise: `significant` = disjoint 95% CIs; `weak` = partial overlap; "
        "`within noise` = >=50% overlap. Do not claim improvements flagged within noise.",
        "",
    ]
    return "\n".join(head + rows) + "\n"


def _f(m: dict[str, Any]) -> str:
    v = m["value"]
    s = f"{v:.4f}" if isinstance(v, float) else str(v)
    if "ci" in m:
        s += f" [{m['ci'][0]:.2f},{m['ci'][1]:.2f}]"
    return s
