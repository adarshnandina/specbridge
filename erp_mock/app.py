"""Mock ERP / parts catalog (separate service, SQLite). Fault injection applies to WRITE calls."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import random
import sqlite3
import threading
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from erp_mock.models import ChangeRequestIn, Faults, PartUpsert

log = logging.getLogger("erp_mock")
logging.basicConfig(level=logging.INFO, format="%(message)s")

SCHEMA = """
CREATE TABLE IF NOT EXISTS parts (
  part_number TEXT PRIMARY KEY, category TEXT, lifecycle_status TEXT NOT NULL DEFAULT 'active',
  spec TEXT NOT NULL, updated_at REAL);
CREATE TABLE IF NOT EXISTS change_requests (
  id TEXT PRIMARY KEY, body TEXT NOT NULL, status TEXT NOT NULL, created_at REAL);
CREATE TABLE IF NOT EXISTS idempotency (
  scope TEXT NOT NULL, key TEXT NOT NULL, body_hash TEXT NOT NULL, status_code INTEGER NOT NULL,
  response TEXT NOT NULL, PRIMARY KEY (scope, key));
"""


def _log(event: str, **kw: Any) -> None:
    log.info(
        json.dumps({"ts": time.time(), "service": "erp-mock", "event": event, **kw}, default=str)
    )


class ErpState:
    def __init__(self, db_path: str, faults: Faults) -> None:
        self.db_path = db_path
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.faults = faults
        self.write_calls = 0
        self.lock = threading.Lock()
        self._mem = (
            sqlite3.connect(":memory:", check_same_thread=False) if db_path == ":memory:" else None
        )
        with self.conn() as c:
            c.executescript(SCHEMA)

    @contextmanager
    def conn(self) -> Iterator[sqlite3.Connection]:
        c = self._mem or sqlite3.connect(self.db_path, check_same_thread=False)
        c.row_factory = sqlite3.Row
        try:
            yield c
            c.commit()
        finally:
            if self._mem is None:
                c.close()


def faults_from_env() -> Faults:
    return Faults(
        failure_rate=float(os.environ.get("ERP_FAILURE_RATE", 0)),
        fail_first_n=int(os.environ.get("ERP_FAIL_FIRST_N", 0)),
        latency_ms=int(os.environ.get("ERP_LATENCY_MS", 0)),
    )


def _hash(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def create_app(db_path: str | None = None, faults: Faults | None = None) -> FastAPI:
    state = ErpState(
        db_path or os.environ.get("ERP_DB_PATH", "data/erp.sqlite"), faults or faults_from_env()
    )
    app = FastAPI(title="SpecBridge ERP mock")
    app.state.erp = state

    @app.middleware("http")
    async def access_log(request: Request, call_next):  # type: ignore[no-untyped-def]
        t0 = time.perf_counter()
        resp = await call_next(request)
        _log(
            "http.request",
            method=request.method,
            path=request.url.path,
            status=resp.status_code,
            latency_ms=int((time.perf_counter() - t0) * 1000),
        )
        return resp

    def inject_write_faults() -> bool:
        """Returns True if the response must be lost AFTER the write executes."""
        with state.lock:
            state.write_calls += 1
            n = state.write_calls
        f = state.faults
        if f.latency_ms:
            time.sleep(f.latency_ms / 1000)
        if n <= f.fail_first_n or (f.failure_rate and random.random() < f.failure_rate):
            _log("fault.injected", write_call=n)
            raise HTTPException(503, "injected ERP failure")
        return f.fail_first_n < n <= f.fail_first_n + f.lose_response_first_n

    def maybe_lose(lose: bool, resp: JSONResponse) -> JSONResponse:
        if lose:
            _log("fault.response_lost", status=resp.status_code)
            raise HTTPException(503, "injected: response lost after write")
        return resp

    def idempotent(scope: str, key: str | None, body: Any, produce) -> JSONResponse:  # type: ignore[no-untyped-def]
        if not key:
            raise HTTPException(400, "Idempotency-Key header is required")
        bh = _hash(body)
        with state.lock, state.conn() as c:
            row = c.execute(
                "SELECT * FROM idempotency WHERE scope=? AND key=?", (scope, key)
            ).fetchone()
            if row:
                if row["body_hash"] != bh:
                    raise HTTPException(409, "Idempotency-Key reused with a different body")
                _log("idempotent.replay", scope=scope, key=key)
                return JSONResponse(json.loads(row["response"]), status_code=row["status_code"])
            code, payload = produce(c)
            c.execute(
                "INSERT INTO idempotency VALUES (?,?,?,?,?)",
                (scope, key, bh, code, json.dumps(payload)),
            )
            return JSONResponse(payload, status_code=code)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    def part_row(r: sqlite3.Row) -> dict[str, Any]:
        return {
            "part_number": r["part_number"],
            "category": r["category"],
            "lifecycle_status": r["lifecycle_status"],
            "spec": json.loads(r["spec"]),
        }

    @app.get("/parts/{part_number}")
    def get_part(part_number: str) -> dict[str, Any]:
        with state.conn() as c:
            r = c.execute("SELECT * FROM parts WHERE part_number=?", (part_number,)).fetchone()
        if not r:
            raise HTTPException(404, f"part {part_number} not found")
        return part_row(r)

    @app.get("/parts")
    def list_parts(category: str | None = None) -> list[dict[str, Any]]:
        with state.conn() as c:
            if category:
                rows = c.execute(
                    "SELECT * FROM parts WHERE category=? ORDER BY part_number", (category,)
                ).fetchall()
            else:
                rows = c.execute("SELECT * FROM parts ORDER BY part_number").fetchall()
        return [part_row(r) for r in rows]

    @app.put("/parts/{part_number}")
    def put_part(
        part_number: str, body: PartUpsert, idempotency_key: str | None = Header(default=None)
    ) -> JSONResponse:
        lose = inject_write_faults()

        def produce(c: sqlite3.Connection) -> tuple[int, dict[str, Any]]:
            old = c.execute(
                "SELECT lifecycle_status FROM parts WHERE part_number=?", (part_number,)
            ).fetchone()
            life = body.lifecycle_status or (old["lifecycle_status"] if old else "active")
            c.execute(
                "INSERT OR REPLACE INTO parts VALUES (?,?,?,?,?)",
                (part_number, body.spec.get("category"), life, json.dumps(body.spec), time.time()),
            )
            return (200 if old else 201), {
                "part_number": part_number,
                "lifecycle_status": life,
                "status": "updated" if old else "created",
            }

        return maybe_lose(
            lose,
            idempotent(f"PUT /parts/{part_number}", idempotency_key, body.model_dump(), produce),
        )

    @app.post("/change-requests")
    def create_cr(
        body: ChangeRequestIn, idempotency_key: str | None = Header(default=None)
    ) -> JSONResponse:
        lose = inject_write_faults()

        def produce(c: sqlite3.Connection) -> tuple[int, dict[str, Any]]:
            cid = str(uuid.uuid4())
            c.execute(
                "INSERT INTO change_requests VALUES (?,?,?,?)",
                (cid, body.model_dump_json(), "created", time.time()),
            )
            return 201, {"id": cid, "status": "created"}

        return maybe_lose(
            lose, idempotent("POST /change-requests", idempotency_key, body.model_dump(), produce)
        )

    def cr_row(r: sqlite3.Row) -> dict[str, Any]:
        return {"id": r["id"], "status": r["status"], **json.loads(r["body"])}

    @app.get("/change-requests/{cid}")
    def get_cr(cid: str) -> dict[str, Any]:
        with state.conn() as c:
            r = c.execute("SELECT * FROM change_requests WHERE id=?", (cid,)).fetchone()
        if not r:
            raise HTTPException(404, "change request not found")
        return cr_row(r)

    @app.get("/change-requests")
    def list_cr() -> list[dict[str, Any]]:
        with state.conn() as c:
            return [
                cr_row(r)
                for r in c.execute("SELECT * FROM change_requests ORDER BY created_at").fetchall()
            ]

    @app.get("/_admin/faults")
    def get_faults() -> dict[str, Any]:
        return {**state.faults.model_dump(), "write_calls": state.write_calls}

    @app.post("/_admin/faults")
    def set_faults(f: Faults) -> dict[str, Any]:
        state.faults = f
        state.write_calls = 0
        _log("faults.set", **f.model_dump())
        return {**f.model_dump(), "write_calls": 0}

    @app.post("/_admin/reset")
    def reset() -> dict[str, str]:
        with state.conn() as c:
            c.execute("DELETE FROM change_requests")
            c.execute("DELETE FROM idempotency")
        state.write_calls = 0
        state.faults = Faults()
        return {"status": "reset"}

    return app


def _default_app() -> FastAPI:
    return create_app()


app = _default_app() if os.environ.get("ERP_AUTOSTART", "1") == "1" else None  # type: ignore[assignment]
