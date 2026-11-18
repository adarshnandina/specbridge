import sqlite3

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from erp_mock.app import create_app as create_erp
from erp_mock.models import Faults
from specbridge.auth.api_keys import Principal
from specbridge.config import Settings
from specbridge.db.models import AuditLog, Document, Extraction
from specbridge.db.session import session_scope
from specbridge.erp_client.client import ErpClient
from specbridge.errors import AppError, ConflictError
from specbridge.extraction import review
from specbridge.extraction.extractor import extract_document
from specbridge.extraction.fake import register_extraction_handlers
from specbridge.ingestion.chunking import ChunkOptions
from specbridge.ingestion.embeddings import get_embedder
from specbridge.ingestion.pipeline import ingest_path
from specbridge.llm.budget import BudgetGuard
from specbridge.llm.fake_provider import FakeProvider
from specbridge.llm.usage import LLMService, MemoryLedger

pytestmark = pytest.mark.integration
ENG = Principal("bob", "engineer")
APPR = Principal("carol", "approver")


@pytest.fixture
def env(db, synth_dir, tmp_path):
    ingest_path(
        synth_dir / "kestrel/KD-110_rev1.0.pdf",
        index="main",
        opts=ChunkOptions("layout"),
        embedder=get_embedder(),
    )
    prov = register_extraction_handlers(FakeProvider())
    ledger = MemoryLedger()
    llm = LLMService(
        prov,
        settings=Settings(_env_file=None, log_llm_payloads=False),
        recorder=ledger.record,
        budget=BudgetGuard(5, ledger.spent),
    )
    erp_db = str(tmp_path / "erp.sqlite")
    erp_http = TestClient(create_erp(erp_db, Faults()))
    erp = ErpClient(erp_http, wait_initial=0.001, wait_max=0.005)
    doc = db.scalars(select(Document)).one()
    return {
        "db": db,
        "llm": llm,
        "prov": prov,
        "erp": erp,
        "erp_http": erp_http,
        "erp_db": erp_db,
        "doc": doc,
    }


def erp_rows(env):
    c = sqlite3.connect(env["erp_db"])
    n = c.execute("SELECT COUNT(*) FROM idempotency").fetchone()[0]
    parts = c.execute("SELECT COUNT(*) FROM parts").fetchone()[0]
    c.close()
    return n, parts


def test_extract_validated_and_matches_ground_truth(env):
    ex = extract_document(env["db"], env["llm"], env["doc"].id)
    assert ex.status == "validated" and ex.attempts == 1 and ex.model and ex.prompt_version
    d = ex.data
    assert d["part_number"] == "KD-110" and d["category"] == "drive"
    assert (d["supply_voltage_min_v"], d["supply_voltage_max_v"]) == (18, 48)
    assert d["interfaces"] == ["CANopen"] and d["ip_rating"] == "IP20"
    assert ex.evidence["ip_rating"]["page"] == 1 and ex.evidence["ip_rating"]["quote"]


def bad_extraction(env):
    good = env["prov"].handlers["extraction"](
        type("R", (), {"messages": [{"content": _page_msg(env)}]})()
    )
    bad = dict(good)
    bad["weight_g"] = {"value": 999, "unit": "g", "page": 1, "quote": "Weight 999 g"}
    return bad, good


def _page_msg(env):
    from specbridge.extraction.extractor import build_message, load_document_pages

    pages, _ = load_document_pages(env["db"], env["doc"])
    return build_message(pages)


def test_validation_failure_goes_to_review_then_edit_approve_push(env):
    bad, good = bad_extraction(env)
    env["prov"].script("extraction", bad, bad)  # fails validation twice -> pending_review
    ex = extract_document(env["db"], env["llm"], env["doc"].id)
    assert ex.status == "pending_review" and ex.attempts == 2
    assert any(
        e["rule"] == "evidence_quote" and e["field"] == "weight_g" for e in ex.validation_errors
    )
    # unreviewed + errors -> cannot approve
    with pytest.raises(ConflictError):
        review.approve(env["db"], ex, APPR)
    # engineer fixes the weight with correct evidence; validation re-runs on save
    ex = review.edit_extraction(
        env["db"],
        ex,
        ENG,
        {"weight_g": 620},
        {"weight_g": {"page": 1, "quote": "Weight [g] 620"}},
        mark_reviewed=True,
    )
    assert ex.status == "validated" and ex.reviewed_by == "bob" and ex.data["weight_g"] == 620
    logs = env["db"].scalars(select(AuditLog).where(AuditLog.action == "extraction.edit")).all()
    assert logs[0].details == {"field": "weight_g", "old": 999, "new": 620}
    ex = review.approve(env["db"], ex, APPR)
    assert ex.status == "approved" and ex.approved_by == "carol"
    ex = review.push(env["db"], ex, APPR, env["erp"])
    assert (
        ex.status == "pushed" and ex.erp_idempotency_key and ex.erp_response["status"] == "created"
    )
    assert env["erp_http"].get("/parts/KD-110").json()["spec"]["weight_g"] == 620
    with pytest.raises(ConflictError):
        review.edit_extraction(env["db"], ex, ENG, {"weight_g": 1})


def test_edit_validation_and_unknown_fields(env):
    ex = extract_document(env["db"], env["llm"], env["doc"].id)
    with pytest.raises(AppError):
        review.edit_extraction(env["db"], ex, ENG, {"nonsense": 1})
    with pytest.raises(AppError):
        review.edit_extraction(env["db"], ex, ENG, {"rated_current_a": "high"})
    with pytest.raises(AppError):
        review.edit_extraction(env["db"], ex, ENG, {"category": "gadget"})
    # an edit that breaks plausibility sends it back to review
    ex = review.edit_extraction(env["db"], ex, ENG, {"operating_temp_max_c": 900})
    assert ex.status == "pending_review"
    assert any(e["rule"] == "plausibility" for e in ex.validation_errors)


def test_reject_and_state_guards(env):
    ex = extract_document(env["db"], env["llm"], env["doc"].id)
    ex = review.reject(env["db"], ex, APPR, "wrong part")
    assert ex.status == "rejected"
    with pytest.raises(ConflictError):
        review.approve(env["db"], ex, APPR)
    with pytest.raises(ConflictError):
        review.push(env["db"], ex, APPR, env["erp"])


def test_push_survives_transient_erp_failures_exactly_once(env):
    ex = extract_document(env["db"], env["llm"], env["doc"].id)
    review.approve(env["db"], ex, APPR)
    env["erp_http"].post("/_admin/faults", json={"fail_first_n": 2})
    ex = review.push(env["db"], ex, APPR, env["erp"])  # 3 attempts: fail, fail, ok
    assert ex.status == "pushed"
    assert erp_rows(env) == (1, 1)
    review.push(env["db"], ex, APPR, env["erp"])  # already pushed: no-op
    assert erp_rows(env) == (1, 1)


def test_push_failure_is_retryable_without_duplicates(env):
    ex = extract_document(env["db"], env["llm"], env["doc"].id)
    review.approve(env["db"], ex, APPR)
    env["erp_http"].post("/_admin/faults", json={"failure_rate": 1.0})
    ex = review.push(env["db"], ex, APPR, env["erp"])
    assert ex.status == "push_failed" and ex.erp_response["retryable"] is True
    assert erp_rows(env) == (0, 0)
    env["erp_http"].post("/_admin/faults", json={})
    ex = review.push(env["db"], ex, APPR, env["erp"])
    assert ex.status == "pushed" and erp_rows(env) == (1, 1)
    audits = [
        a.outcome
        for a in env["db"].scalars(
            select(AuditLog).where(AuditLog.action == "extraction.push").order_by(AuditLog.ts)
        )
    ]
    assert audits == ["error", "allowed"]


def test_idempotency_key_is_deterministic(env):
    ex = extract_document(env["db"], env["llm"], env["doc"].id)
    from specbridge.erp_client.client import idempotency_key

    assert idempotency_key(str(ex.id), "1") == idempotency_key(str(ex.id), "1")
    assert idempotency_key(str(ex.id), "1") != idempotency_key(str(ex.id), "2")
    assert len(idempotency_key("a", "b")) == 64
    assert session_scope  # silence unused import in some configurations
    assert env["db"].scalars(select(Extraction)).all()
