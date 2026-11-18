import pytest

from specbridge.ingestion.chunking import ChunkOptions
from specbridge.ingestion.embeddings import get_embedder
from specbridge.ingestion.pipeline import ingest_directory

pytestmark = pytest.mark.integration


@pytest.fixture
def api(client, synth_dir, tmp_path):
    """API with seeded corpus, GT-seeded extractions and an in-process ERP."""
    from fastapi.testclient import TestClient
    from sqlalchemy import select

    from corpus.synthetic.ground_truth import load_ground_truth
    from erp_mock.app import create_app as create_erp
    from erp_mock.models import Faults
    from erp_mock.seed import seed
    from specbridge.api.deps import set_erp
    from specbridge.db.models import Document, Extraction
    from specbridge.db.session import session_scope
    from specbridge.erp_client.client import ErpClient
    from specbridge.llm.fake_handlers import register_all_handlers

    ingest_directory(synth_dir, index="main", opts=ChunkOptions("layout"), embedder=get_embedder())
    with session_scope() as s:
        docs = {d.doc_key: d for d in s.scalars(select(Document))}
        for r in load_ground_truth():
            if r["doc_key"] in docs:
                s.add(
                    Extraction(
                        document_id=docs[r["doc_key"]].id,
                        model="gt-seed",
                        prompt_version="seed",
                        status="approved",
                        data=r["spec"],
                        evidence={},
                        validation_errors=[],
                        attempts=0,
                    )
                )
    erp_db = str(tmp_path / "erp.sqlite")
    seed(erp_db)
    http = TestClient(create_erp(erp_db, Faults()))
    set_erp(ErpClient(http, wait_initial=0.001, wait_max=0.005))
    register_all_handlers(client.fake)
    client.erp_http = http
    yield client
    set_erp(None)


REQ = {"request": "Find a replacement for discontinued part KD-240"}


def test_agent_api_flow_with_roles(api, headers):
    assert api.post("/agent/runs", json=REQ, headers=headers["viewer"]).status_code == 403
    r = api.post("/agent/runs", json=REQ, headers=headers["engineer"])
    assert r.status_code == 201
    run = r.json()
    assert run["state"] == "AWAITING_APPROVAL" and run["approval_status"] == "pending"
    rid, aid = run["id"], run["approval_id"]
    steps = api.get(f"/agent/runs/{rid}/steps", headers=headers["viewer"]).json()
    assert [s["step_no"] for s in steps] == list(range(1, len(steps) + 1))
    assert any(s["tool_name"] == "search_parts" for s in steps)
    pend = api.get("/approvals?status=pending", headers=headers["viewer"]).json()
    assert [a["id"] for a in pend] == [aid]
    # engineer cannot approve (permission); requester-approver cannot approve own (four-eyes)
    assert api.post(f"/approvals/{aid}/approve", headers=headers["engineer"]).status_code == 403
    assert (
        api.get(f"/agent/runs/{rid}", headers=headers["viewer"]).json()["state"]
        == "AWAITING_APPROVAL"
    )
    ok = api.post(
        f"/approvals/{aid}/approve", json={"comment": "lgtm"}, headers=headers["approver"]
    )
    assert ok.status_code == 200 and ok.json()["decided_by"] == "carol"
    assert api.get(f"/agent/runs/{rid}", headers=headers["viewer"]).json()["state"] == "DONE"
    assert len(api.erp_http.get("/change-requests").json()) == 1
    assert api.post(f"/approvals/{aid}/approve", headers=headers["approver"]).status_code == 409
    assert (
        api.post("/agent/runs", json={"request": "x"}, headers=headers["engineer"]).status_code
        == 422
    )
    assert (
        api.get(
            "/agent/runs/00000000-0000-0000-0000-000000000000", headers=headers["viewer"]
        ).status_code
        == 404
    )


def test_four_eyes_via_api_and_retry_endpoint(api, headers):
    r = api.post("/agent/runs", json=REQ, headers=headers["approver"]).json()  # carol requests
    resp = api.post(f"/approvals/{r['approval_id']}/approve", headers=headers["approver"])
    assert resp.status_code == 403 and "Four-eyes" in resp.json()["error"]["message"]
    assert (
        api.post(f"/approvals/{r['approval_id']}/reject", headers=headers["admin"]).status_code
        == 200
    )
    assert (
        api.get(f"/agent/runs/{r['id']}", headers=headers["viewer"]).json()["state"] == "REJECTED"
    )
    # retry on a non-failed run is a conflict
    assert api.post(f"/agent/runs/{r['id']}/retry", headers=headers["engineer"]).status_code == 409


def test_failed_commit_then_retry_endpoint(api, headers):
    api.erp_http.post("/_admin/faults", json={"failure_rate": 1.0})
    r = api.post("/agent/runs", json=REQ, headers=headers["engineer"]).json()
    api.post(f"/approvals/{r['approval_id']}/approve", headers=headers["approver"])
    run = api.get(f"/agent/runs/{r['id']}", headers=headers["viewer"]).json()
    assert run["state"] == "FAILED" and run["result"]["retryable"] is True
    api.erp_http.post("/_admin/faults", json={})
    done = api.post(f"/agent/runs/{r['id']}/retry", headers=headers["engineer"]).json()
    assert done["state"] == "DONE" and len(api.erp_http.get("/change-requests").json()) == 1


def test_agent_ui_pages_and_actions(api, headers):
    api.post("/ui/login", data={"api_key": "dev-engineer-key"})
    r = api.post("/ui/runs", data={"request": REQ["request"]}, follow_redirects=False)
    assert r.status_code == 303
    page = api.get(r.headers["location"])
    assert (
        page.status_code == 200 and "AWAITING_APPROVAL" in page.text and "search_parts" in page.text
    )
    assert "RECEIVED" in page.text and "retrieve_evidence" in page.text
    appr = api.get("/ui/approvals")
    assert "KD-240" in appr.text and "Approve" not in appr.text  # engineer: no buttons
    api.cookies.clear()
    api.post("/ui/login", data={"api_key": "dev-approver-key"})
    appr = api.get("/ui/approvals")
    assert "Approve" in appr.text
    aid = appr.text.split("/ui/approvals/")[1].split("/decide")[0]
    dec = api.post(
        f"/ui/approvals/{aid}/decide",
        data={"decision": "approve", "comment": "ok"},
        follow_redirects=False,
    )
    assert dec.status_code == 303
    assert "approved" in api.get("/ui/approvals").text
    assert "DONE" in api.get("/ui/runs").text
    bad = api.post(
        f"/ui/approvals/{aid}/decide", data={"decision": "maybe"}, follow_redirects=False
    )
    assert bad.status_code in (400, 409)
