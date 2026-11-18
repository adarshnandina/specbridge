from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, text
from testcontainers.postgres import PostgresContainer

from alembic import command


def alembic_cfg(url: str) -> Config:
    cfg = Config("alembic.ini")
    cfg.attributes["url"] = url
    return cfg


@pytest.fixture(scope="session")
def pg_url() -> Iterator[str]:
    with PostgresContainer(
        "pgvector/pgvector:pg16", username="sb", password="sb", dbname="sb", driver="psycopg"
    ) as pg:
        url = pg.get_connection_url()
        os.environ["DATABASE_URL"] = url
        from specbridge.config import get_settings
        from specbridge.db.session import reset_engine

        get_settings.cache_clear()
        reset_engine()
        command.upgrade(alembic_cfg(url), "head")
        yield url


@pytest.fixture
def db(pg_url: str) -> Iterator[object]:
    """A clean database per test: truncate all data tables, then yield a session."""
    from specbridge.db.session import get_engine, session_scope

    with get_engine().begin() as c:
        c.execute(
            text(
                "TRUNCATE approvals, agent_steps, agent_runs, extractions, chunks, pages, "
                "documents, audit_log, llm_calls, query_logs RESTART IDENTITY CASCADE"
            )
        )
    with session_scope() as s:
        yield s


@pytest.fixture(scope="session")
def raw_engine(pg_url: str):  # type: ignore[no-untyped-def]
    return create_engine(pg_url)


H = {
    "viewer": {"X-API-Key": "dev-viewer-key"},
    "engineer": {"X-API-Key": "dev-engineer-key"},
    "engineer2": {"X-API-Key": "dev-engineer2-key"},
    "approver": {"X-API-Key": "dev-approver-key"},
    "admin": {"X-API-Key": "dev-admin-key"},
}


@pytest.fixture
def headers() -> dict[str, dict[str, str]]:
    return H


@pytest.fixture(scope="session")
def synth_dir(tmp_path_factory):  # type: ignore[no-untyped-def]
    from corpus.synthetic.generator import generate

    d = tmp_path_factory.mktemp("synth_shared")
    generate(42, d / "synthetic", d / "gt.jsonl")
    return d / "synthetic"


@pytest.fixture
def client(db, tmp_path, monkeypatch):  # type: ignore[no-untyped-def]
    """TestClient with a fake LLM; DATA_DIR isolated per test."""
    from fastapi.testclient import TestClient

    from specbridge.api.main import create_app
    from specbridge.api.routers import query as qrouter
    from specbridge.config import Settings, get_settings
    from specbridge.llm.budget import BudgetGuard
    from specbridge.llm.fake_provider import FakeProvider
    from specbridge.llm.usage import LLMService, MemoryLedger

    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    get_settings.cache_clear()
    ledger = MemoryLedger()
    provider = FakeProvider()
    llm = LLMService(
        provider,
        settings=Settings(_env_file=None, log_llm_payloads=False),
        recorder=ledger.record,
        budget=BudgetGuard(5, ledger.spent),
    )
    qrouter.set_llm(llm)
    c = TestClient(create_app())
    c.fake = provider  # type: ignore[attr-defined]
    c.ledger = ledger  # type: ignore[attr-defined]
    yield c
    qrouter.set_llm(None)
    get_settings.cache_clear()
