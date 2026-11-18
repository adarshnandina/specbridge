import json

from prometheus_client import generate_latest

from corpus.synthetic.judge_calibration import build
from specbridge.config import Settings, get_settings
from specbridge.eval.datasets import read_jsonl, validate_datasets
from specbridge.llm.base import LLMRequest
from specbridge.llm.budget import BudgetGuard
from specbridge.llm.fake_provider import FakeProvider
from specbridge.llm.usage import LLMService, MemoryLedger
from specbridge.logging_setup import get_logger, setup_logging


def test_budget_remaining_gauge_is_updated():
    ledger = MemoryLedger()
    p = FakeProvider()
    p.script("qa", "hi")
    svc = LLMService(
        p,
        settings=Settings(_env_file=None, log_llm_payloads=False),
        recorder=ledger.record,
        budget=BudgetGuard(5.0, ledger.spent),
    )
    svc.complete(LLMRequest(messages=[], purpose="qa"))
    assert "sb_llm_budget_remaining_usd 5.0" in generate_latest().decode()


def test_every_log_line_has_request_context_fields(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LOG_DIR", str(tmp_path))
    get_settings.cache_clear()
    setup_logging(force=True)
    get_logger("specbridge.test").info("plain.event")
    line = next(ln for ln in capsys.readouterr().out.splitlines() if "plain.event" in ln)
    rec = json.loads(line)
    assert {"ts", "level", "event", "request_id", "actor", "role", "module"} <= set(rec)
    assert rec["request_id"] is None
    get_settings.cache_clear()


def test_judge_calibration_dataset_shape_and_empty_scores():
    rows = read_jsonl("eval/datasets/judge_calibration.jsonl")
    assert len(rows) == 20 and all(r["human_score"] is None for r in rows)
    assert {r["candidate_kind"] for r in rows} == {"faithful", "wrong_voltage"}
    assert all(r["answer_source"].startswith("programmatic") for r in rows)
    wrong = next(r for r in rows if r["candidate_kind"] == "wrong_voltage")
    assert wrong["candidate_answer"] != wrong["reference_answer"]
    assert [r["id"] for r in build()] == [r["id"] for r in rows]
    assert validate_datasets() == []
