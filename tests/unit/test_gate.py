import copy
import json
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from specbridge.cli import app
from specbridge.eval.gate import evaluate, run_gate
from specbridge.eval.stats import proportion

T = yaml.safe_load(Path("eval/thresholds.yaml").read_text())


def run(
    rid="r",
    recall5=0.90,
    mrr=0.70,
    p95=25.0,
    acc=0.80,
    cite=0.90,
    abst=0.90,
    cost=0.05,
    qa_p95=1000.0,
    f1=0.95,
    safety=True,
    split="dev",
    datasets=None,
):
    return {
        "run_id": rid,
        "split": split,
        "provider": "fake",
        "config": {},
        "suites": ["x"],
        "datasets": datasets or {"qa.jsonl": "h1"},
        "aggregates": {
            "retrieval": {
                "overall": {
                    "recall_at_5": proportion(round(recall5 * 100), 100),
                    "mrr": {"value": mrr, "n": 100},
                }
            },
            "qa": {
                "accuracy": proportion(round(acc * 100), 100),
                "citation_precision": proportion(round(cite * 100), 100),
                "abstention_recall": proportion(round(abst * 100), 100),
            },
            "extraction": {"micro_f1": {"value": f1, "n": 100}},
            "agent": {
                "safety_all_pass": safety,
                "failures": [] if safety else [{"id": "S10", "safety": True, "failures": ["x"]}],
            },
        },
        "ops": {
            "retrieval": {"retrieval_latency_ms": {"n": 5, "p50": 20, "p95": p95}},
            "qa": {
                "total_latency_ms": {"n": 5, "p50": 500, "p95": qa_p95},
                "cost_per_100_queries": cost,
            },
        },
    }


def failed(base, cand):
    return {c.name for c in evaluate(base, cand, T) if not c.ok}


def test_identical_runs_pass():
    assert failed(run(), run()) == set()


@pytest.mark.parametrize(
    "kw,expected",
    [
        ({"recall5": 0.86}, {"retrieval.recall_at_5"}),  # drop 0.04 > 0.03
        ({"recall5": 0.88}, set()),  # drop 0.02 within threshold
        ({"mrr": 0.66}, {"retrieval.mrr"}),
        ({"acc": 0.76}, {"qa.accuracy"}),
        ({"cite": 0.85}, {"qa.citation_precision"}),
        ({"abst": 0.84}, {"qa.abstention_recall"}),  # drop 0.06 > 0.05
        ({"abst": 0.86}, set()),  # drop 0.04 within 0.05
        ({"f1": 0.92}, {"extraction.micro_f1"}),
        ({"f1": 0.94}, set()),
        ({"qa_p95": 1300.0}, {"ops.qa.p95_total_latency_ms"}),  # +30% and > noise floor
        ({"qa_p95": 1200.0}, set()),  # +20%
        ({"cost": 0.07}, {"ops.qa.cost_per_100_queries"}),  # +40%
        ({"safety": False}, {"agent.safety_scenarios"}),
    ],
)
def test_threshold_boundaries(kw, expected):
    assert failed(run(), run(**kw)) == expected


def test_improvements_never_fail():
    assert failed(run(), run(recall5=0.99, mrr=0.95, acc=0.95, p95=5.0, cost=0.01)) == set()


def test_latency_noise_floor_ignores_small_absolute_changes():
    # 25 ms -> 40 ms is +60% but only +15 ms (< 20 ms floor): not a regression
    assert failed(run(p95=25.0), run(p95=40.0)) == set()
    assert "ops.retrieval.p95_latency_ms" in failed(run(p95=25.0), run(p95=60.0))


def test_suite_filter_and_missing_metrics():
    checks = evaluate(run(), run(recall5=0.5), T, suites=["qa"])
    assert all(c.name.startswith(("qa", "ops.qa")) for c in checks)
    partial = {"run_id": "p", "split": "dev", "datasets": {}, "aggregates": {}, "ops": {}}
    assert evaluate(run(), partial, T) == []


def write(tmp, name, r):
    p = tmp / name
    p.write_text(json.dumps(r))
    return p


def test_run_gate_detects_deliberate_regression(tmp_path):
    base = write(tmp_path, "baseline.json", run("base"))
    good = write(tmp_path, "good.json", run("good", recall5=0.91))
    bad = write(tmp_path, "bad.json", run("bad", recall5=0.60, mrr=0.40))
    ok, rep = run_gate(base, str(good), suites=["retrieval"])
    assert ok and "Gate PASSED" in rep
    ok, rep = run_gate(base, str(bad), suites=["retrieval"])
    assert not ok and "**FAIL**" in rep and "Gate FAILED" in rep


def test_gate_rejects_incomparable_runs(tmp_path):
    base = write(tmp_path, "b.json", run("b"))
    other_split = write(tmp_path, "c.json", run("c", split="test"))
    other_data = write(tmp_path, "d.json", run("d", datasets={"qa.jsonl": "DIFFERENT"}))
    assert not run_gate(base, str(other_split))[0]
    ok, rep = run_gate(base, str(other_data))
    assert not ok and "dataset hashes differ" in rep
    assert run_gate(base, str(other_data), allow_dataset_change=True)[0]


def test_cli_exit_codes(tmp_path):
    base = write(tmp_path, "baseline.json", run("base"))
    bad = write(tmp_path, "bad.json", run("bad", recall5=0.5))
    good = write(tmp_path, "good.json", copy.deepcopy(run("good")))
    r = CliRunner()
    assert (
        r.invoke(
            app,
            [
                "eval",
                "gate",
                "--baseline",
                str(base),
                "--candidate",
                str(good),
                "--suite",
                "retrieval",
            ],
        ).exit_code
        == 0
    )
    assert (
        r.invoke(
            app,
            [
                "eval",
                "gate",
                "--baseline",
                str(base),
                "--candidate",
                str(bad),
                "--suite",
                "retrieval",
            ],
        ).exit_code
        == 1
    )
    assert (
        r.invoke(
            app,
            [
                "eval",
                "gate",
                "--baseline",
                str(tmp_path / "missing.json"),
                "--candidate",
                str(good),
            ],
        ).exit_code
        == 2
    )


def test_unrelated_dataset_change_does_not_block_a_suite_gate(tmp_path):
    base = write(
        tmp_path, "b.json", run("b", datasets={"qa.jsonl": "h", "agent_scenarios.yaml": "A"})
    )
    cand = write(
        tmp_path, "c.json", run("c", datasets={"qa.jsonl": "h", "agent_scenarios.yaml": "B"})
    )
    assert run_gate(base, str(cand), suites=["retrieval"])[0]  # agent file irrelevant
    cand2 = write(tmp_path, "d.json", run("d", datasets={"qa.jsonl": "CHANGED"}))
    ok, rep = run_gate(base, str(cand2), suites=["retrieval"])
    assert not ok and "qa.jsonl" in rep
