"""Run the retrieval-side experiments (1-4, 7) and write eval_results/experiments_<split>.json.

python -m specbridge.eval.experiments [--split dev|test] [--only exp1-chunking-fixed ...]

Experiments 5 and 6 need a paid LLM and are run by `specbridge eval run --suite extraction`
once an API key is configured (see experiments/exp5*.yaml, exp6*.yaml).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from sqlalchemy import func, select

from specbridge.config import get_settings
from specbridge.db.models import Chunk
from specbridge.db.session import session_scope
from specbridge.eval.runner import load_config, run_eval
from specbridge.ingestion.chunking import ChunkOptions
from specbridge.ingestion.pipeline import ingest_directory

EXPERIMENTS = [
    ("exp1", "exp1-chunking-layout", "retrieval"),
    ("exp1", "exp1-chunking-fixed", "retrieval"),
    ("exp1", "exp1-chunking-fixed-header", "retrieval"),
    ("exp2", "exp2-mode-vector", "retrieval"),
    ("exp2", "exp2-mode-keyword", "retrieval"),
    ("exp2", "exp2-mode-hybrid", "retrieval"),
    ("exp3", "exp3-hybrid-rerank", "retrieval"),
    ("exp4", "exp4-header-on", "retrieval"),
    ("exp4", "exp4-header-off", "retrieval"),
    ("exp7", "exp7-abstain-calibration", "calibration"),
]
INDEXES = {  # index name -> chunk options
    "main": ChunkOptions("layout", context_header=True),
    "exp_fixed": ChunkOptions("fixed", context_header=False),
    "exp_nohdr": ChunkOptions("layout", context_header=False),
    "exp_fixed_hdr": ChunkOptions("fixed", context_header=True),
}


def ensure_indexes(corpus: Path) -> None:
    for name, opts in INDEXES.items():
        with session_scope() as s:
            n = s.scalar(select(func.count()).select_from(Chunk).where(Chunk.index_name == name))
        if not n:
            ingest_directory(corpus, index=name, opts=opts)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="dev")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--corpus", default="data/corpus")
    ap.add_argument("--render", action="store_true", help="print markdown tables from saved runs")
    a = ap.parse_args()
    if a.render:
        print(render_tables(a.split))
        return
    ensure_indexes(Path(a.corpus))
    index_file = Path("eval_results") / f"experiments_{a.split}.json"
    done: dict[str, Any] = json.loads(index_file.read_text()) if index_file.exists() else {}
    for group, name, suite in EXPERIMENTS:
        if a.only and name not in a.only:
            continue
        cfg = load_config(Path("experiments") / f"{name}.yaml")
        r = run_eval([suite], a.split, cfg, name, provider="fake")
        done[name] = {"group": group, "run_id": r["run_id"], "suite": suite, "split": a.split}
        print(f"{name}: {r['run_id']}")
    index_file.write_text(json.dumps(done, indent=1))
    print(f"wrote {index_file} (embedding model {get_settings().embedding_model})")


def render_tables(split: str) -> str:
    """Markdown tables for docs/EXPERIMENTS.md, generated from the run files (never hand-typed)."""
    from specbridge.eval.compare import load_run
    from specbridge.eval.stats import noise_flag

    idx = json.loads((Path("eval_results") / f"experiments_{split}.json").read_text())
    refs = {
        "exp1": "exp1-chunking-layout",
        "exp2": "exp2-mode-hybrid",
        "exp3": "exp2-mode-hybrid",
        "exp4": "exp4-header-on",
    }
    out: list[str] = []
    for group, title in (
        ("exp1", "Experiment 1 - chunking"),
        ("exp2", "Experiment 2 - retrieval mode"),
        ("exp3", "Experiment 3 - reranker"),
        ("exp4", "Experiment 4 - context header"),
    ):
        rows = [(n, v) for n, v in idx.items() if v["group"] == group and v["suite"] == "retrieval"]
        if group == "exp3":
            rows = [("exp2-mode-hybrid", idx["exp2-mode-hybrid"])] + rows
        ref = load_run(idx[refs[group]]["run_id"])["aggregates"]["retrieval"]["overall"]
        out += [
            f"**{title}** ({split} split)",
            "",
            "| config | run id | R@1 | R@3 | R@5 [95% CI] | R@10 | MRR | R@5 vs ref | MRR vs ref | p50 ms | n |",
            "|---|---|---|---|---|---|---|---|---|---|---|",
        ]
        for name, v in rows:
            r = load_run(v["run_id"])
            o = r["aggregates"]["retrieval"]["overall"]
            lat = r["ops"]["retrieval"]["retrieval_latency_ms"]
            is_ref = v["run_id"] == idx[refs[group]]["run_id"]
            r5 = o["recall_at_5"]
            out.append(
                f"| {name} | `{v['run_id']}` | {o['recall_at_1']['value']:.3f} | "
                f"{o['recall_at_3']['value']:.3f} | {r5['value']:.3f} [{r5['ci'][0]:.2f}, {r5['ci'][1]:.2f}] | "
                f"{o['recall_at_10']['value']:.3f} | {o['mrr']['value']:.3f} | "
                f"{'(reference)' if is_ref else noise_flag(ref['recall_at_5'], r5)} | "
                f"{'(reference)' if is_ref else _mrr_flag(ref, o)} | {lat['p50']:.0f} | {o['n']} |"
            )
        out.append("")
    cal = load_run(idx["exp7-abstain-calibration"]["run_id"])["aggregates"]["calibration"]
    out += [
        f"**Experiment 7 - abstention threshold** ({split} split, run "
        f"`{idx['exp7-abstain-calibration']['run_id']}`)",
        "",
        f"mean top vector similarity: answerable {cal['score_summary']['answerable_mean']:.3f} "
        f"(n={cal['score_summary']['n_answerable']}), unanswerable "
        f"{cal['score_summary']['unanswerable_mean']:.3f} (n={cal['score_summary']['n_unanswerable']})",
        "",
        "| threshold | abstained | abstention precision | abstention recall | answerable questions blocked |",
        "|---|---|---|---|---|",
    ]
    for row in cal["curve"]:
        if round(row["threshold"], 2) in (0.55, 0.60, 0.62, 0.65, 0.70, 0.75):
            p_, r_, o_ = row["precision"], row["recall"], row["over_abstention"]
            out.append(
                f"| {row['threshold']:.2f} | {row['abstained']} | {p_['k']}/{p_['n']} | "
                f"{r_['k']}/{r_['n']} | {o_['k']}/{o_['n']} |"
            )
    out.append("")
    return "\n".join(out)


def _mrr_flag(ref: dict[str, Any], o: dict[str, Any]) -> str:
    """MRR is a mean, not a proportion: report the sign and mark it 'n/a' for noise (no CI)."""
    d = o["mrr"]["value"] - ref["mrr"]["value"]
    return f"{d:+.3f} (no CI)"


if __name__ == "__main__":
    main()
