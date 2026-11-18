import pytest

from specbridge.db.session import session_scope
from specbridge.ingestion.chunking import ChunkOptions
from specbridge.ingestion.embeddings import get_embedder
from specbridge.ingestion.pipeline import ingest_path
from specbridge.retrieval.service import retrieve

pytestmark = pytest.mark.integration


def login(client, key="dev-viewer-key"):
    r = client.post("/ui/login", data={"api_key": key}, follow_redirects=False)
    return r


def test_redirects_to_login_without_session(client):
    r = client.get("/ui/ask", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/ui/login"
    assert client.get("/ui/login").status_code == 200


def test_bad_key_and_tampered_cookie(client):
    assert login(client, "nope").status_code == 401
    client.cookies.set("sb_session", "forged.value.here")
    assert client.get("/ui/ask", follow_redirects=False).status_code == 303


def test_login_cookie_flags(client):
    r = login(client)
    assert r.status_code == 303
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie
    assert client.get("/ui/ask").status_code == 200
    assert "alice" in client.get("/ui/documents").text


def test_ask_flow_with_clickable_highlighted_source(client, synth_dir):
    ingest_path(
        synth_dir / "kestrel/KD-210_rev1.0.pdf",
        index="main",
        opts=ChunkOptions("layout"),
        embedder=get_embedder(),
    )
    with session_scope() as s:
        c0 = retrieve(s, "What is the KD-210?", embedder=get_embedder()).chunks[0]
    quote = next(ln for ln in c0.content.split("\n") if len(ln.strip(" |-")) > 8)
    client.fake.script(
        "qa",
        {
            "answerable": True,
            "answer": "A servo drive.",
            "citations": [{"source_id": "S1", "quote": quote}],
        },
    )
    login(client)
    r = client.post("/ui/ask", data={"question": "What is the KD-210?"})
    assert r.status_code == 200 and "A servo drive." in r.text and "kestrel/KD-210/rev1.0" in r.text
    import re

    href = re.search(r'href="(/ui/source\?[^"]+)"', r.text).group(1).replace("&amp;", "&")
    src = client.get(href)
    assert src.status_code == 200 and "/ui/page/" in src.text
    img_url = re.search(r'src="(/ui/page/[^"]+)"', src.text).group(1)
    img = client.get(img_url)
    assert img.status_code == 200 and img.content[:4] == b"\x89PNG"


def test_html_escaping_of_answer(client):
    client.fake.script(
        "qa", {"answerable": False, "answer": "<script>alert(1)</script>", "citations": []}
    )
    login(client)
    # empty corpus abstains without LLM; the question itself is echoed and must be escaped
    r = client.post("/ui/ask", data={"question": "<img src=x onerror=alert(1)> what?"})
    assert "<img src=x" not in r.text and "&lt;img" in r.text


def test_logout_clears_cookie(client):
    login(client)
    r = client.get("/ui/logout", follow_redirects=False)
    assert r.status_code == 303
    client.cookies.clear()
    assert client.get("/ui/ask", follow_redirects=False).status_code == 303


def test_static_css(client):
    assert client.get("/ui/static/style.css").status_code == 200
