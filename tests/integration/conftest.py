from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from testcontainers.postgres import PostgresContainer


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
        c.execute(text(
            "TRUNCATE approvals, agent_steps, agent_runs, extractions, chunks, pages, "
            "documents, audit_log, llm_calls, query_logs RESTART IDENTITY CASCADE"
        ))
    with session_scope() as s:
        yield s


@pytest.fixture(scope="session")
def raw_engine(pg_url: str):  # type: ignore[no-untyped-def]
    return create_engine(pg_url)
