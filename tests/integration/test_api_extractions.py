import re
import sqlite3

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from erp_mock.app import create_app as create_erp
from erp_mock.models import Faults
from specbridge.api.deps import set_erp
from specbridge.db.models import AuditLog
from specbridge.db.session import session_scope
from specbridge.erp_client.client import ErpClient
from specbridge.extraction.fake import register_extraction_handlers
from tests.integration.test_api_docs_query import upload

pytestmark = pytest.mark.integration


@pytest.fixture
def api(client, headers, synth_dir, tmp_path):
    register_extraction_handlers(client.fake)
    erp_db = str(tmp_path / "erp.sqlite")
    erp_http = TestClient(create_erp(erp_db, Faults()))
    set_erp(ErpClient(erp_http, wait_initial=0.001, wait_max=0.005))
    client.erp_http, client.erp_db = erp_http, erp_db
    doc = upload(client, headers, synth_dir / "kestrel/KD-110_rev1.0.pdf").json()["document"]
    client.doc_id = doc["id"]
    yield client
    set_erp(None)


def create(api, headers):
    r = api.post("/extractions", json={"document_id": api.doc_id}, headers=headers["engineer"])
    assert r.status_code == 201, r.text
    return r.json()


def test_full_api_flow_roles_and_push(api, headers):
    ex = create(api, headers)
    assert ex["status"] == "validated" and ex["data"]["part_number"] == "KD-110"
    eid = ex["id"]
    # viewer: read only
    assert api.get(f"/extractions/{eid}", headers=headers["viewer"]).status_code == 200
    assert (
        api.post(
            "/extractions", json={"document_id": api.doc_id}, headers=headers["viewer"]
        ).status_code
        == 403
    )
    assert (
        api.patch(f"/extractions/{eid}", json={"edits": {}}, headers=headers["viewer"]).status_code
        == 403
    )
    # engineer cannot approve or push
    assert api.post(f"/extractions/{eid}/approve", headers=headers["engineer"]).status_code == 403
    assert api.post(f"/extractions/{eid}/push", headers=headers["engineer"]).status_code == 403
    # push before approval -> 409
    assert api.post(f"/extractions/{eid}/push", headers=headers["approver"]).status_code == 409
    r = api.post(f"/extractions/{eid}/approve", headers=headers["approver"])
    assert r.status_code == 200 and r.json()["approved_by"] == "carol"
    r = api.post(f"/extractions/{eid}/push", headers=headers["approver"])
    assert r.json()["status"] == "pushed"
    assert (
        api.post(f"/extractions/{eid}/push", headers=headers["approver"]).json()["status"]
        == "pushed"
    )
    c = sqlite3.connect(api.erp_db)
    assert c.execute("SELECT COUNT(*) FROM idempotency").fetchone()[0] == 1
    assert api.erp_http.get("/parts/KD-110").json()["spec"]["category"] == "drive"
    with session_scope() as s:
        actions = {a.action for a in s.scalars(select(AuditLog))}
        assert {"extraction.create", "extraction.approve", "extraction.push"} <= actions
        assert s.scalars(select(AuditLog).where(AuditLog.outcome == "denied")).all()


def test_patch_and_list_and_errors(api, headers):
    ex = create(api, headers)
    r = api.patch(
        f"/extractions/{ex['id']}",
        json={
            "edits": {"weight_g": 700},
            "evidence": {"weight_g": {"page": 1, "quote": "Weight [g] 620"}},
            "mark_reviewed": True,
        },
        headers=headers["engineer"],
    )
    assert r.status_code == 200
    body = r.json()
    assert body["data"]["weight_g"] == 700 and body["status"] == "pending_review"  # 620 != 700
    assert body["reviewed_by"] == "bob"
    r = api.patch(
        f"/extractions/{ex['id']}", json={"edits": {"bogus": 1}}, headers=headers["engineer"]
    )
    assert r.status_code == 400 and r.json()["error"]["code"] == "invalid_edit"
    lst = api.get("/extractions?status=pending_review", headers=headers["viewer"]).json()
    assert [e["id"] for e in lst] == [ex["id"]]
    assert (
        api.get(
            "/extractions/00000000-0000-0000-0000-000000000000", headers=headers["viewer"]
        ).status_code
        == 404
    )
    assert (
        api.post(
            "/extractions",
            json={"document_id": "00000000-0000-0000-0000-000000000000"},
            headers=headers["engineer"],
        ).status_code
        == 404
    )


def test_push_failure_then_retry_via_api(api, headers):
    ex = create(api, headers)
    api.post(f"/extractions/{ex['id']}/approve", headers=headers["approver"])
    api.erp_http.post("/_admin/faults", json={"failure_rate": 1.0})
    r = api.post(f"/extractions/{ex['id']}/push", headers=headers["approver"])
    assert r.json()["status"] == "push_failed"
    api.erp_http.post("/_admin/faults", json={})
    r = api.post(f"/extractions/{ex['id']}/push", headers=headers["approver"])
    assert r.json()["status"] == "pushed"


def test_review_ui_flow(api, headers):
    ex = create(api, headers)
    eid = ex["id"]
    r = api.post("/ui/login", data={"api_key": "dev-engineer-key"}, follow_redirects=False)
    assert r.status_code == 303
    page = api.get("/ui/review")
    assert page.status_code == 200 and "KD-110" in page.text
    detail = api.get(f"/ui/review/{eid}")
    assert detail.status_code == 200 and "v__weight_g" in detail.text
    assert "Approve" not in detail.text  # engineer has no approve permission
    save = api.post(
        f"/ui/review/{eid}/edit", data={"v__part_number": "KD-110", "v__weight_g": "abc"}
    )
    assert "not a number" in save.text
    # approver sees approve button and can push
    api.cookies.clear()
    api.post("/ui/login", data={"api_key": "dev-approver-key"})
    assert "Approve" in api.get(f"/ui/review/{eid}").text
    api.post(f"/ui/review/{eid}/approve", follow_redirects=False)
    assert re.search(r"Push to ERP", api.get(f"/ui/review/{eid}").text)
    api.post(f"/ui/review/{eid}/push", follow_redirects=False)
    assert api.get(f"/extractions/{eid}", headers=headers["viewer"]).json()["status"] == "pushed"
