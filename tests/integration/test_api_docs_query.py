import pytest
from sqlalchemy import select

from specbridge.db.models import AuditLog, Document
from specbridge.db.session import session_scope

pytestmark = pytest.mark.integration


def upload(client, headers, path, who="engineer"):
    with open(path, "rb") as fh:
        return client.post(
            "/documents", files={"file": (path.name, fh, "application/pdf")}, headers=headers[who]
        )


def test_auth_required_and_error_format(client, headers):
    r = client.get("/documents")
    assert r.status_code == 401
    body = r.json()["error"]
    assert body["code"] == "unauthorized" and body["request_id"] == r.headers["X-Request-ID"]
    assert client.get("/documents", headers={"X-API-Key": "wrong"}).status_code == 401


def test_viewer_cannot_upload_and_denial_audited(client, headers, synth_dir):
    r = upload(client, headers, synth_dir / "kestrel/KD-210_rev1.0.pdf", who="viewer")
    assert r.status_code == 403 and r.json()["error"]["code"] == "forbidden"
    with session_scope() as s:
        row = s.scalars(select(AuditLog).where(AuditLog.outcome == "denied")).one()
        assert row.actor == "alice" and row.role == "viewer"


def test_upload_list_get_and_idempotent(client, headers, synth_dir):
    f = synth_dir / "kestrel/KD-210_rev1.0.pdf"
    r = upload(client, headers, f)
    assert r.status_code == 201 and r.json()["status"] == "ingested"
    doc = r.json()["document"]
    assert doc["doc_key"] == "kestrel/KD-210/rev1.0" and doc["page_count"] == 1
    assert upload(client, headers, f).json()["status"] == "skipped"
    lst = client.get("/documents", headers=headers["viewer"]).json()
    assert len(lst) == 1
    assert client.get(f"/documents/{doc['id']}", headers=headers["viewer"]).status_code == 200
    assert (
        client.get(
            "/documents/00000000-0000-0000-0000-000000000000", headers=headers["viewer"]
        ).status_code
        == 404
    )
    with session_scope() as s:
        assert s.scalars(select(AuditLog).where(AuditLog.action == "document.upload")).all()


def test_upload_rejects_non_pdf_and_oversize(client, headers, monkeypatch):
    r = client.post(
        "/documents",
        files={"file": ("x.pdf", b"GIF89a....", "application/pdf")},
        headers=headers["engineer"],
    )
    assert r.status_code == 400 and r.json()["error"]["code"] == "invalid_upload"
    from specbridge.config import get_settings

    monkeypatch.setenv("MAX_UPLOAD_MB", "1")
    get_settings.cache_clear()
    big = b"%PDF-1.4" + b"0" * (2 * 1024 * 1024)
    r = client.post(
        "/documents",
        files={"file": ("big.pdf", big, "application/pdf")},
        headers=headers["engineer"],
    )
    assert r.status_code == 400


def test_query_and_highlighted_page_image(client, headers, synth_dir):
    upload(client, headers, synth_dir / "kestrel/KD-210_rev1.0.pdf")
    client.fake.script(
        "qa",
        {
            "answerable": True,
            "answer": "It is a servo drive.",
            "citations": [{"source_id": "S1", "quote": "Product group"}],
        },
    )
    # S1 may be text or table chunk; use a quote guaranteed present via retrieval
    from specbridge.ingestion.embeddings import get_embedder
    from specbridge.retrieval.service import retrieve

    with session_scope() as s:
        c0 = retrieve(s, "What is the KD-210?", embedder=get_embedder()).chunks[0]
    quote = next(ln for ln in c0.content.split("\n") if len(ln.strip(" |-")) > 8)
    client.fake.queues["qa"].clear()
    client.fake.script(
        "qa",
        {
            "answerable": True,
            "answer": "It is a servo drive.",
            "citations": [{"source_id": "S1", "quote": quote}],
        },
    )
    r = client.post("/query", json={"question": "What is the KD-210?"}, headers=headers["viewer"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert not body["abstained"] and body["citations"] and body["request_id"]
    url = body["citations"][0]["image_url"]
    img = client.get(url, headers=headers["viewer"])
    assert img.status_code == 200 and img.headers["content-type"] == "image/png"
    assert img.content[:8] == b"\x89PNG\r\n\x1a\n"
    plain = client.get(url.split("?")[0], headers=headers["viewer"])
    assert plain.content != img.content  # highlighted differs from plain page
    cached = client.get(url, headers=headers["viewer"])
    assert cached.content == img.content
    assert (
        client.get(url.replace("pages/1", "pages/9"), headers=headers["viewer"]).status_code == 404
    )


def test_query_validation_and_auth(client, headers):
    assert (
        client.post("/query", json={"question": "hi"}, headers=headers["viewer"]).status_code == 422
    )
    assert client.post("/query", json={"question": "What is X?"}).status_code == 401
    r = client.post(
        "/query", json={"question": "What is X?", "mode": "bogus"}, headers=headers["viewer"]
    )
    assert r.status_code == 422


def test_query_abstains_on_empty_corpus(client, headers):
    r = client.post("/query", json={"question": "What is the KD-210?"}, headers=headers["viewer"])
    assert r.status_code == 200 and r.json()["abstained"] and client.ledger.rows == []


def test_documents_in_db(client, headers, synth_dir):
    upload(client, headers, synth_dir / "kestrel/KD-210_rev1.0.pdf")
    with session_scope() as s:
        assert s.scalars(select(Document)).one().source_type == "upload"


def test_upload_hardening_page_limit_and_filename(client, headers, synth_dir, monkeypatch):
    from specbridge.ingestion import pipeline

    path = synth_dir / "kestrel/KD-210_rev1.0.pdf"
    with open(path, "rb") as fh:
        r = client.post(
            "/documents",
            files={"file": ("../../etc/passwd.pdf", fh, "application/pdf")},
            headers=headers["engineer"],
        )
    assert r.status_code == 201
    doc = r.json()["document"]
    assert doc["filename"] == "passwd.pdf"  # path components stripped
    monkeypatch.setattr(pipeline, "MAX_PAGES", 0)
    other = synth_dir / "kestrel/KD-110_rev1.0.pdf"
    with open(other, "rb") as fh:
        r = client.post(
            "/documents",
            files={"file": ("a.pdf", fh, "application/pdf")},
            headers=headers["engineer"],
        )
    assert r.status_code == 400 and "pages" in r.json()["error"]["message"]


def test_audit_endpoint_admin_only_with_filters(client, headers, synth_dir):
    upload(client, headers, synth_dir / "kestrel/KD-210_rev1.0.pdf")  # allowed
    upload(client, headers, synth_dir / "kestrel/KD-110_rev1.0.pdf", who="viewer")  # denied
    for who in ("viewer", "engineer", "approver"):
        assert client.get("/audit", headers=headers[who]).status_code == 403
    assert client.get("/audit").status_code == 401
    rows = client.get("/audit", headers=headers["admin"]).json()
    assert {r["outcome"] for r in rows} >= {"allowed", "denied"}
    assert any(r["action"] == "document.upload" and r["actor"] == "bob" for r in rows)
    denied = client.get("/audit?outcome=denied", headers=headers["admin"]).json()
    assert denied and all(r["outcome"] == "denied" for r in denied)
    assert all(
        r["actor"] == "alice"
        for r in client.get("/audit?actor=alice", headers=headers["admin"]).json()
    )
    by_action = client.get("/audit?action=document.upload", headers=headers["admin"]).json()
    assert by_action and {r["action"] for r in by_action} == {"document.upload"}
    assert client.get("/audit?since=2999-01-01T00:00:00Z", headers=headers["admin"]).json() == []
    assert client.get("/audit?outcome=bogus", headers=headers["admin"]).status_code == 422
    assert client.get("/audit?limit=1", headers=headers["admin"]).json().__len__() == 1
    assert all(r["request_id"] for r in rows[:1])
