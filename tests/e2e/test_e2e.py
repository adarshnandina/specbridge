"""End-to-end tests against `docker compose up` (db, erp-mock, api). Run: make test-e2e."""

from __future__ import annotations

import os
import time
from pathlib import Path

import httpx
import pytest

pytestmark = pytest.mark.e2e
API = os.environ.get("E2E_API", "http://localhost:8000")
ERP = os.environ.get("E2E_ERP", "http://localhost:8100")
KEYS = {"viewer": "dev-viewer-key", "engineer": "dev-engineer-key", "approver": "dev-approver-key"}


def h(role: str) -> dict[str, str]:
    return {"X-API-Key": KEYS[role]}


@pytest.fixture(scope="module")
def api() -> httpx.Client:
    c = httpx.Client(base_url=API, timeout=60)
    deadline = time.time() + 120
    while time.time() < deadline:
        try:
            if c.get("/ready").status_code == 200:
                return c
        except httpx.HTTPError:
            pass
        time.sleep(2)
    pytest.fail("stack did not become ready: is `docker compose up` running?")


@pytest.fixture(scope="module")
def pdfs(tmp_path_factory) -> Path:
    from corpus.synthetic.generator import generate

    d = tmp_path_factory.mktemp("e2e")
    generate(42, d / "synthetic", d / "gt.jsonl")
    return d / "synthetic"


def upload(api: httpx.Client, path: Path) -> dict:
    with open(path, "rb") as fh:
        r = api.post(
            "/documents", files={"file": (path.name, fh, "application/pdf")}, headers=h("engineer")
        )
    assert r.status_code == 201, r.text
    return r.json()


def test_health_ready_and_metrics(api):
    assert api.get("/health").json() == {"status": "ok"}
    ready = api.get("/ready")
    assert ready.status_code == 200 and ready.json()["checks"] == {
        "database": "ok",
        "embedding_model": "ok",
        "erp": "ok",
    }
    assert "sb_http_requests_total" in api.get("/metrics").text
    assert api.get("/documents").status_code == 401  # auth enforced in the container too


def test_upload_query_and_highlighted_page_image(api, pdfs):
    up = upload(api, pdfs / "kestrel" / "KD-210_rev1.0.pdf")
    assert up["document"]["doc_key"] == "kestrel/KD-210/rev1.0"
    r = api.post(
        "/query",
        headers=h("viewer"),
        json={"question": "What is the protection class of the KD-210?", "top_k": 30},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert not body["abstained"] and body["citations"] and body["request_id"]
    cite = next(c for c in body["citations"] if "KD-210" in c["doc_key"])
    img = api.get(cite["image_url"], headers=h("viewer"))
    assert img.status_code == 200 and img.headers["content-type"] == "image/png"
    assert img.content[:8] == b"\x89PNG\r\n\x1a\n"
    plain = api.get(cite["image_url"].split("?")[0], headers=h("viewer"))
    assert plain.content != img.content  # highlight is drawn


def test_agent_happy_path_with_approval_by_a_different_user(api, pdfs):
    # candidate datasheets must be extracted so the agent can search them
    for pn in ("KD-210", "KD-230", "KD-250", "KD-320", "KD-350"):
        doc = upload(api, pdfs / "kestrel" / f"{pn}_rev1.0.pdf")["document"]
        r = api.post("/extractions", headers=h("engineer"), json={"document_id": doc["id"]})
        assert r.status_code == 201, r.text
        api.post(
            f"/extractions/{r.json()['id']}/approve", headers=h("approver")
        )  # 409 if unreviewed
    before = len(httpx.get(f"{ERP}/change-requests", timeout=10).json())
    run = api.post(
        "/agent/runs",
        headers=h("engineer"),
        json={"request": "Find a replacement for discontinued part KD-240"},
    )
    assert run.status_code == 201, run.text
    run = run.json()
    assert run["state"] == "AWAITING_APPROVAL", run
    assert (
        len(httpx.get(f"{ERP}/change-requests", timeout=10).json()) == before
    )  # nothing written yet
    # the requester cannot approve (and is not an approver anyway)
    assert (
        api.post(f"/approvals/{run['approval_id']}/approve", headers=h("engineer")).status_code
        == 403
    )
    ok = api.post(
        f"/approvals/{run['approval_id']}/approve", headers=h("approver"), json={"comment": "e2e"}
    )
    assert ok.status_code == 200, ok.text
    final = api.get(f"/agent/runs/{run['id']}", headers=h("viewer")).json()
    assert final["state"] == "DONE"
    assert len(httpx.get(f"{ERP}/change-requests", timeout=10).json()) == before + 1
    steps = api.get(f"/agent/runs/{run['id']}/steps", headers=h("viewer")).json()
    assert [s["tool_name"] for s in steps if s["tool_name"] == "create_change_request"] == [
        "create_change_request"
    ]
