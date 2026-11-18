import json

import pytest
import yaml

from specbridge.config import Settings
from specbridge.eval.compare import all_metrics, compare_runs, flatten
from specbridge.eval.runner import (
    RunConfig,
    SuiteContext,
    estimate_cost,
    load_config,
    render_markdown,
)
from specbridge.eval.stats import proportion


def run(rid, k, n, p95=100.0, cost=1.0):
    return {
        "run_id": rid,
        "split": "dev",
        "provider": "fake",
        "config": {},
        "suites": ["qa"],
        "created_at": "x",
        "git_sha": "abc",
        "cost_usd": cost,
        "prompt_versions": [],
        "models": {},
        "notes": [],
        "duration_s": 1,
        "aggregates": {"qa": {"accuracy": proportion(k, n)}},
        "ops": {
            "qa": {
                "total_latency_ms": {"n": 5, "p50": 50.0, "p95": p95, "mean": 60.0},
                "cost_per_100_queries": cost,
            }
        },
    }


def test_flatten_and_ops_metrics():
    r = run("a", 8, 10)
    m = all_metrics(r)
    assert "qa.accuracy" in m and "ops.qa.total_latency_ms.p95" in m
    assert flatten({"x": {"y": {"value": 1, "n": 2}}}) == {"x.y": {"value": 1, "n": 2}}


def test_compare_flags_noise_and_significance():
    md = compare_runs(run("a", 80, 100), run("b", 82, 100))
    line = next(row for row in md.splitlines() if row.startswith("| qa.accuracy"))
    assert "within noise" in line and "+0.0200" in line
    md2 = compare_runs(run("a", 20, 100), run("b", 90, 100))
    assert "significant" in next(r for r in md2.splitlines() if r.startswith("| qa.accuracy"))


def test_load_config(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text(yaml.safe_dump({"name": "x", "retrieval": {"mode": "vector", "top_k": 5}}))
    c = load_config(p)
    assert c.name == "x" and c.retrieval["mode"] == "vector"
    assert load_config(None) == RunConfig()
    p.write_text("unknown: 1\nname: y\n")
    assert load_config(p).name == "y"


def test_estimate_cost_fake_free_and_paid_positive():
    s = Settings(_env_file=None)
    free = SuiteContext(s, RunConfig(), "dev", False, "fake")
    paid = SuiteContext(s, RunConfig(), "dev", False, "anthropic")
    assert estimate_cost("qa", 100, free) == 0.0
    c = estimate_cost("qa", 100, paid)
    assert 0 < c < 2.0  # a 100-question haiku run stays well under the default cap
    assert estimate_cost("qa", 1000, paid) == pytest.approx(10 * c)
    assert estimate_cost("retrieval", 100, paid) == 0.0


def test_render_markdown_contains_ci_and_note():
    r = run("a", 8, 10)
    r["aggregates"]["qa"].update(
        {
            k: proportion(1, 2)
            for k in (
                "abstention_precision",
                "abstention_recall",
                "over_abstention_rate",
                "injection_resistance",
                "citation_precision",
                "citation_coverage",
                "revision_stale_rate",
            )
        }
    )
    r["aggregates"]["qa"]["judge_usefulness"] = {"value": None, "n": 0}
    r["aggregates"]["qa"]["accuracy_by_type"] = {"factual": proportion(1, 2)}
    r["notes"] = ["fake provider: pipeline check only"]
    md = render_markdown(r)
    assert "[0.490, 0.943]" in md and "pipeline check only" in md and json.dumps(r["config"]) in md
