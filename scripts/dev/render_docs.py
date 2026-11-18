#!/usr/bin/env python3
"""Regenerate docs/EXPERIMENTS.md, docs/EVALUATION.md and README.md from eval_results/.

Tables and every metric value are read from run files (never typed). Prose that quotes a number
is written against the current runs: re-read it after re-running experiments.

usage: render_docs.py <baseline-run-id-or-'baseline'> <final-test-run-id>
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load(x: str) -> dict:
    p = ROOT / "eval_results" / (x if x.endswith(".json") else x + ".json")
    return json.loads(p.read_text())


def m(x: dict, digits: int = 3, n: bool = True) -> str:
    s = f"{x['value']:.{digits}f} [{x['ci'][0]:.2f}, {x['ci'][1]:.2f}]"
    return s + (f" (n={x['n']})" if n else "")


def tables(split: str) -> str:
    out = subprocess.run(
        [sys.executable, "-m", "specbridge.eval.experiments", "--split", split, "--render"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout


def sect(t: str, title: str) -> str:
    a = t.index(title)
    b = t.find("**Experiment", a + 5)
    return t[a : b if b != -1 else len(t)].strip()


def experiments(dev: str, test: str) -> str:
    titles = [
        "**Experiment 1 - chunking**",
        "**Experiment 2 - retrieval mode**",
        "**Experiment 3 - reranker**",
        "**Experiment 4 - context header**",
        "**Experiment 7 - abstention threshold**",
    ]
    S = {k: (sect(dev, k), sect(test, k)) for k in titles}
    return (
        (ROOT / "scripts/dev/EXPERIMENTS.template.md")
        .read_text()
        .format(
            **{f"d{i}": S[t][0] for i, t in enumerate(titles)},
            **{f"t{i}": S[t][1] for i, t in enumerate(titles)},
        )
    )


def main() -> None:
    base = load(sys.argv[1])
    test = load(sys.argv[2])
    dev_t, test_t = tables("dev"), tables("test")
    (ROOT / "docs/EXPERIMENTS.md").write_text(experiments(dev_t, test_t))
    for name, fn in (("EVALUATION", "EVALUATION.template.md"), ("README", "README.template.md")):
        tpl = (ROOT / "scripts/dev" / fn).read_text()
        rb, rt = (
            base["aggregates"]["retrieval"]["overall"],
            test["aggregates"]["retrieval"]["overall"],
        )
        qb, qt = base["aggregates"]["qa"], test["aggregates"]["qa"]
        eb, et = base["aggregates"]["extraction"], test["aggregates"]["extraction"]
        ab, at = base["aggregates"]["agent"], test["aggregates"]["agent"]
        erb, ert = (
            base["aggregates"].get("extraction_real"),
            test["aggregates"].get("extraction_real"),
        )
        rows = [
            ("retrieval recall@1", m(rb["recall_at_1"]), m(rt["recall_at_1"])),
            ("retrieval recall@3", m(rb["recall_at_3"]), m(rt["recall_at_3"])),
            ("retrieval recall@5", m(rb["recall_at_5"]), m(rt["recall_at_5"])),
            ("retrieval recall@10", m(rb["recall_at_10"]), m(rt["recall_at_10"])),
            (
                "retrieval MRR",
                f"{rb['mrr']['value']:.3f} (n={rb['mrr']['n']})",
                f"{rt['mrr']['value']:.3f} (n={rt['mrr']['n']})",
            ),
        ]
        for key, label in (
            ("accuracy", "QA answer accuracy"),
            ("abstention_recall", "QA abstention recall"),
            ("abstention_precision", "QA abstention precision"),
            ("injection_resistance", "QA injection resistance"),
            ("citation_precision", "QA citation precision"),
            ("citation_coverage", "QA citation coverage"),
        ):
            rows.append((f"{label} **(fake)**", m(qb[key]), m(qt[key])))
        rows += [
            (
                "extraction micro-F1, synthetic **(fake)**",
                f"{eb['micro_f1']['value']:.3f} (n={eb['n_documents']} docs)",
                f"{et['micro_f1']['value']:.3f} (n={et['n_documents']} docs)",
            ),
            (
                "extraction: share auto-validated **(fake)**",
                m(eb["auto_validated_rate"]),
                m(et["auto_validated_rate"]),
            ),
            (
                "extraction: precision of validated docs **(fake)**",
                m(eb["validated_doc_precision"]),
                m(et["validated_doc_precision"]),
            ),
        ]
        if erb and ert:
            rows.append(
                (
                    "extraction micro-F1, real labels **(fake, PROVISIONAL)**",
                    f"{erb['micro_f1']['value']:.3f} (n={erb['n_documents']} docs)",
                    f"{ert['micro_f1']['value']:.3f} (n={ert['n_documents']} docs)",
                )
            )
        rows += [
            ("agent scenarios passed", m(ab["pass_rate"]), m(at["pass_rate"])),
            (
                "agent safety scenarios passed (6 must pass)",
                m(ab["safety_pass_rate"]),
                m(at["safety_pass_rate"]),
            ),
        ]
        table = "\n".join(f"| {a} | {b} | {c} |" for a, b, c in rows)
        lat = base["ops"]["retrieval"]["retrieval_latency_ms"]
        out = tpl.format(
            BASE_ID=base["run_id"],
            TEST_ID=test["run_id"],
            TABLE=table,
            R1=f"{rb['recall_at_1']['value']:.2f}",
            R5D=f"{rb['recall_at_5']['value']:.2f}",
            R5T=f"{rt['recall_at_5']['value']:.2f}",
            LAT50=f"{lat['p50']:.0f}",
            LAT95=f"{lat['p95']:.0f}",
            RETR_ROW5=f"{m(rb['recall_at_5'], 2)} | {m(rt['recall_at_5'], 2)}",
            RETR_ROW1=f"{m(rb['recall_at_1'], 2)} | {m(rt['recall_at_1'], 2)}",
            MRR=f"{rb['mrr']['value']:.2f} | {rt['mrr']['value']:.2f}",
            AGENT=f"{m(ab['pass_rate'], 2)} | {m(at['pass_rate'], 2)}",
            SAFETY=f"{m(ab['safety_pass_rate'], 2)} | {m(at['safety_pass_rate'], 2)}",
            QAACC=f"{m(qb['accuracy'], 2)} | {m(qt['accuracy'], 2)}",
            EXF1=f"{eb['micro_f1']['value']:.2f} | {et['micro_f1']['value']:.2f}",
        )
        (ROOT / ("README.md" if name == "README" else "docs/EVALUATION.md")).write_text(out)


if __name__ == "__main__":
    main()
