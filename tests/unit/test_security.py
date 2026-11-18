import json
import logging

import pytest
from fastapi.testclient import TestClient

from specbridge.config import Settings, get_settings
from specbridge.llm.base import LLMRequest
from specbridge.llm.budget import BudgetGuard
from specbridge.llm.fake_provider import FakeProvider
from specbridge.llm.usage import LLMService, MemoryLedger
from specbridge.logging_setup import get_logger, redact_text, redact_value, setup_logging


@pytest.fixture
def app_factory(monkeypatch):
    def make(**env):
        for k, v in env.items():
            monkeypatch.setenv(k, str(v))
        get_settings.cache_clear()
        from specbridge.api.main import create_app

        return TestClient(create_app())

    yield make
    get_settings.cache_clear()


def test_rate_limit_is_per_api_key(app_factory):
    c = app_factory(RATE_LIMIT="3/minute")
    statuses = [
        c.get("/ui/login", headers={"X-API-Key": "dev-viewer-key"}).status_code for _ in range(5)
    ]
    assert statuses[:3] == [200, 200, 200] and statuses[3:] == [429, 429]
    other = c.get("/ui/login", headers={"X-API-Key": "dev-engineer-key"})
    assert other.status_code == 200  # a different key has its own budget
    r = c.get("/ui/login", headers={"X-API-Key": "dev-viewer-key"})
    assert r.status_code == 429
    err = r.json()["error"]
    assert err["code"] == "rate_limited" and err["request_id"] == r.headers["X-Request-ID"]


def test_secrets_redacted_in_log_values_and_headers():
    assert "sk-ant-api03-abc" not in redact_text("key=sk-ant-api03-abc_DEF-1")
    assert "AKIAABCDEFGHIJKLMNOP" not in redact_text("AKIAABCDEFGHIJKLMNOP")
    assert "hunter2" not in redact_text("aws_secret_access_key = hunter2")
    out = redact_value(
        {
            "headers": {"X-API-Key": "dev-viewer-key", "Authorization": "Bearer t", "ok": "fine"},
            "api_key": "x",
        }
    )
    assert (
        out["headers"]["X-API-Key"] == "[REDACTED]"
        and out["headers"]["Authorization"] == "[REDACTED]"
    )
    assert out["api_key"] == "[REDACTED]" and out["headers"]["ok"] == "fine"


def test_request_logs_never_contain_api_key(app_factory, tmp_path, monkeypatch, capsys):
    c = app_factory(LOG_DIR=str(tmp_path / "logs"), LOG_LEVEL="INFO")
    setup_logging(force=True)
    secret = "dev-viewer-key"
    c.get("/documents", headers={"X-API-Key": secret})  # 401 path would log too
    c.get("/health", headers={"X-API-Key": secret, "Authorization": "Bearer supersecrettoken"})
    for h in logging.getLogger().handlers:
        h.flush()
    text = (tmp_path / "logs" / "app.jsonl").read_text() + capsys.readouterr().out
    assert "http.request" in text
    assert secret not in text and "supersecrettoken" not in text


def test_llm_payload_log_redacts_configured_key(tmp_path):
    key = "sk-ant-api03-SUPERSECRETVALUE"
    s = Settings(_env_file=None, log_llm_payloads=True, log_dir=tmp_path, anthropic_api_key=key)
    ledger = MemoryLedger()
    p = FakeProvider()
    p.script("qa", f"echo {key}")
    svc = LLMService(p, settings=s, recorder=ledger.record, budget=BudgetGuard(5, ledger.spent))
    svc.complete(
        LLMRequest(messages=[{"role": "user", "content": f"my key is {key}"}], purpose="qa")
    )
    body = (tmp_path / "llm_payloads.jsonl").read_text()
    assert key not in body and "SUPERSECRETVALUE" not in body and "[REDACTED]" in body
    assert json.loads(body.splitlines()[0])["purpose"] == "qa"


def test_error_logging_of_provider_failure_is_redacted(tmp_path):
    key = "sk-ant-api03-LEAKYERROR"
    s = Settings(_env_file=None, log_llm_payloads=False, log_dir=tmp_path)
    ledger = MemoryLedger()
    p = FakeProvider()
    p.script("qa", RuntimeError(f"401 invalid key {key}"))
    svc = LLMService(p, settings=s, recorder=ledger.record, budget=BudgetGuard(5, ledger.spent))
    with pytest.raises(RuntimeError):
        svc.complete(LLMRequest(messages=[], purpose="qa"))
    assert key not in (ledger.rows[0]["error"] or "")


def test_logger_has_required_fields(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LOG_DIR", str(tmp_path))
    get_settings.cache_clear()
    setup_logging(force=True)
    get_logger("specbridge.test").info("unit.event", foo=1)
    line = [ln for ln in capsys.readouterr().out.splitlines() if "unit.event" in ln][0]
    rec = json.loads(line)
    assert {"ts", "level", "event", "module"} <= set(rec) and rec["foo"] == 1
    get_settings.cache_clear()


def test_health_and_metrics_are_not_rate_limited(app_factory):
    c = app_factory(RATE_LIMIT="2/minute")
    assert all(c.get("/health", headers={"X-API-Key": "k"}).status_code == 200 for _ in range(6))
    assert all(c.get("/metrics").status_code == 200 for _ in range(6))


def test_storage_paths_are_relative_and_resolve_after_a_move(tmp_path, monkeypatch):
    from specbridge.ingestion import storage

    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data1"))
    get_settings.cache_clear()
    data = b"%PDF-1.4 minimal"
    sha = storage.validate_pdf_bytes(data)
    abs_path = storage.store_pdf(data, sha)
    rel = storage.relative_path(sha)
    assert rel == f"documents/{sha}.pdf" and abs_path.read_bytes() == data
    assert storage.resolve_path(rel, sha) == abs_path
    # a legacy absolute path from another machine still resolves through DATA_DIR
    assert storage.resolve_path(f"/Users/someone/else/{sha}.pdf", sha) == abs_path
    # data dir moved
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data2"))
    get_settings.cache_clear()
    (tmp_path / "data2" / "documents").mkdir(parents=True)
    (tmp_path / "data2" / "documents" / f"{sha}.pdf").write_bytes(data)
    assert storage.resolve_path(rel, sha) == tmp_path / "data2" / "documents" / f"{sha}.pdf"
    get_settings.cache_clear()
