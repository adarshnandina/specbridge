"""Agent scenario suite (registered with the eval runner). Hermetic: ephemeral database."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from specbridge.agent.scenarios import SAFETY_IDS, AgentEnv, load_scenarios, run_all
from specbridge.db.admin import ephemeral_database
from specbridge.eval.metrics import latency_summary
from specbridge.eval.runner import SuiteContext, SuiteOutput, register_suite
from specbridge.eval.stats import proportion
from specbridge.ingestion.embeddings import get_embedder


def run_agent_suite(ctx: SuiteContext) -> SuiteOutput:
    pdf_dir = Path(ctx.settings.data_dir) / "corpus" / "synthetic"
    if not pdf_dir.exists():
        from corpus.synthetic.generator import generate

        generate(42, pdf_dir, Path("eval/datasets/extraction_synthetic.jsonl"))
    scenarios = load_scenarios()
    with tempfile.TemporaryDirectory() as tmp, ephemeral_database():
        env = AgentEnv(pdf_dir, ctx.embedder or get_embedder(), Path(tmp) / "erp.sqlite")
        env.prepare()
        results = run_all(env, scenarios)
    safety = [r for r in results if r.safety]
    failures = [
        {"id": r.id, "failures": r.failures, "safety": r.safety} for r in results if not r.passed
    ]
    agg: dict[str, Any] = {
        "agent": {
            "pass_rate": proportion(sum(r.passed for r in results), len(results)),
            "safety_pass_rate": proportion(sum(r.passed for r in safety), len(safety)),
            "safety_all_pass": bool(safety) and all(r.passed for r in safety),
            "scenarios": len(results),
            "failures": failures,
            "safety_ids": list(SAFETY_IDS),
        }
    }
    items = [
        {
            "id": r.id,
            "safety": r.safety,
            "passed": r.passed,
            "failures": r.failures,
            "final_state": r.facts.get("final_state"),
            "erp_change_requests": r.facts.get("erp_change_requests"),
            "tool_calls_ok": r.facts.get("tool_calls_ok"),
            "tool_calls_denied": r.facts.get("tool_calls_denied"),
            "denied_actions": r.facts.get("denied_actions"),
            "duration_ms": r.duration_ms,
        }
        for r in results
    ]
    notes = [
        "scenarios run against the FakeProvider with scripted model behaviours (incl. a "
        "'compromised model' that follows injected instructions); safety is enforced by code, "
        "not by the model. A live-LLM agent run is blocked: needs API key"
    ]
    ops = {"scenario_duration_ms": latency_summary(r.duration_ms for r in results)}
    return SuiteOutput(items, agg, ops, 0.0, {}, ["agent_parse.v1", "agent_compare.v1"], notes)


register_suite("agent", run_agent_suite)
