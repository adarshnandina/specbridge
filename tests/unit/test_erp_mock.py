import pytest
from fastapi.testclient import TestClient

from erp_mock.app import create_app
from erp_mock.models import Faults
from erp_mock.seed import seed


@pytest.fixture
def client(tmp_path):
    db = str(tmp_path / "erp.sqlite")
    seed(db)
    return TestClient(create_app(db, Faults()))


H = {"Idempotency-Key": "k1"}
CR = {"original_part": "KD-240", "proposed_part": "KD-210", "rationale": "r", "requested_by": "bob"}


def test_seed_and_reads(client):
    r = client.get("/parts/KD-240")
    assert r.status_code == 200 and r.json()["lifecycle_status"] == "discontinued"
    assert client.get("/parts/NOPE").status_code == 404
    drives = client.get("/parts", params={"category": "drive"}).json()
    assert drives and all(p["category"] == "drive" for p in drives)
    assert len(client.get("/parts").json()) == 46


def test_idempotency_required_and_replay(client):
    assert client.post("/change-requests", json=CR).status_code == 400
    a = client.post("/change-requests", json=CR, headers=H)
    b = client.post("/change-requests", json=CR, headers=H)
    assert a.status_code == 201 and b.json() == a.json()
    assert len(client.get("/change-requests").json()) == 1
    c = client.post("/change-requests", json={**CR, "proposed_part": "KD-230"}, headers=H)
    assert c.status_code == 409
    assert client.get(f"/change-requests/{a.json()['id']}").json()["proposed_part"] == "KD-210"


def test_put_part_upsert_idempotent(client):
    body = {"spec": {"category": "sensor", "part_number": "X-1"}}
    r1 = client.put("/parts/X-1", json=body, headers={"Idempotency-Key": "a"})
    r2 = client.put("/parts/X-1", json=body, headers={"Idempotency-Key": "a"})
    assert r1.status_code == 201 and r2.json() == r1.json()
    r3 = client.put("/parts/X-1", json=body, headers={"Idempotency-Key": "b"})
    assert r3.status_code == 200 and r3.json()["status"] == "updated"
    assert (
        client.put(
            "/parts/X-1", json={"spec": {"x": 1}}, headers={"Idempotency-Key": "a"}
        ).status_code
        == 409
    )


def test_fail_first_n_then_ok_and_no_duplicate(client):
    client.post("/_admin/faults", json={"fail_first_n": 2})
    assert client.post("/change-requests", json=CR, headers=H).status_code == 503
    assert client.post("/change-requests", json=CR, headers=H).status_code == 503
    assert client.post("/change-requests", json=CR, headers=H).status_code == 201
    assert len(client.get("/change-requests").json()) == 1
    assert client.get("/parts/KD-240").status_code == 200  # reads unaffected


def test_failure_rate_and_reset(client):
    client.post("/_admin/faults", json={"failure_rate": 1.0})
    assert client.post("/change-requests", json=CR, headers=H).status_code == 503
    assert client.get("/_admin/faults").json()["failure_rate"] == 1.0
    client.post("/_admin/reset")
    assert client.post("/change-requests", json=CR, headers=H).status_code == 201


def test_latency(client):
    client.post("/_admin/faults", json={"latency_ms": 50})
    import time

    t = time.perf_counter()
    client.post("/change-requests", json=CR, headers=H)
    assert time.perf_counter() - t >= 0.05
