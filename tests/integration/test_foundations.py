import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, select

from alembic import command
from specbridge import audit
from specbridge.api.deps import audit_denied
from specbridge.api.main import create_app
from specbridge.auth.api_keys import Principal
from specbridge.config import Settings
from specbridge.db.models import AuditLog, LLMCall
from specbridge.db.session import session_scope
from specbridge.llm.base import LLMRequest
from specbridge.llm.budget import BudgetGuard
from specbridge.llm.fake_provider import FakeProvider
from specbridge.llm.usage import LLMService, db_recorder, db_spent_today
from tests.integration.conftest import alembic_cfg

pytestmark = pytest.mark.integration


def test_migrations_up_down_up(pg_url):
    cfg = alembic_cfg(pg_url)
    command.downgrade(cfg, "base")
    eng = create_engine(pg_url)
    assert "chunks" not in inspect(eng).get_table_names()
    command.upgrade(cfg, "head")
    tables = set(inspect(eng).get_table_names())
    assert {
        "documents",
        "pages",
        "chunks",
        "extractions",
        "agent_runs",
        "agent_steps",
        "approvals",
        "audit_log",
        "llm_calls",
        "query_logs",
    } <= tables


def test_audit_and_denied_survive(db):
    audit.record(db, actor="a", role="viewer", action="x", outcome="allowed")
    audit_denied(Principal("bob", "viewer"), "POST /documents")
    with session_scope() as s:
        outcomes = {r.outcome for r in s.execute(select(AuditLog)).scalars()}
    assert "denied" in outcomes


def test_llm_call_rows_and_budget(db):
    p = FakeProvider()
    p.script("qa", "hi", "again")
    s = Settings(_env_file=None, log_llm_payloads=False, llm_daily_budget_usd=5.0)
    svc = LLMService(p, settings=s, recorder=db_recorder, budget=BudgetGuard(5.0, db_spent_today))
    svc.complete(LLMRequest(messages=[{"role": "user", "content": "q"}], purpose="qa"))
    with session_scope() as sess:
        row = sess.execute(select(LLMCall)).scalars().one()
        assert row.purpose == "qa" and row.input_tokens > 0
    assert db_spent_today() == 0.0


def test_ready_reports_erp_down_and_db_ok(db):
    c = TestClient(create_app())
    r = c.get("/ready")
    assert r.json()["checks"]["database"] == "ok"
    assert r.json()["checks"]["embedding_model"] == "ok"
    assert r.status_code == 503  # no ERP running in this test
