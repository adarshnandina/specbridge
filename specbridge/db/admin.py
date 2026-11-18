"""Ephemeral databases for hermetic evaluation runs."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from alembic import command
from specbridge.config import get_settings
from specbridge.db.session import use_database

ROOT = Path(__file__).resolve().parents[2]


def migrate(url: str) -> None:
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "alembic"))
    cfg.attributes["url"] = url
    command.upgrade(cfg, "head")


@contextmanager
def ephemeral_database() -> Iterator[str]:
    """Create a throw-away database on the configured server, migrate it, point the engine at it,
    and drop it afterwards. Requires CREATE DATABASE rights."""
    base = make_url(get_settings().database_url)
    name = f"specbridge_eval_{uuid.uuid4().hex[:10]}"
    admin = create_engine(base.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as c:
        c.execute(text(f'CREATE DATABASE "{name}"'))
    url = base.set(database=name).render_as_string(hide_password=False)
    try:
        migrate(url)
        with use_database(url):
            yield url
    finally:
        with admin.connect() as c:
            c.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        admin.dispose()
