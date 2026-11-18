from fastapi.testclient import TestClient

from specbridge.api.main import create_app


def test_health_and_request_id():
    c = TestClient(create_app())
    r = c.get("/health", headers={"X-Request-ID": "abc"})
    assert r.status_code == 200 and r.headers["X-Request-ID"] == "abc"
    assert "X-Request-ID" in c.get("/health").headers


def test_metrics_exposed():
    c = TestClient(create_app())
    c.get("/health")
    assert "sb_http_requests_total" in c.get("/metrics").text


def test_error_format_404():
    c = TestClient(create_app())
    r = c.get("/nope")
    assert r.status_code == 404
