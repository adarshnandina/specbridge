from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from specbridge.config import get_settings

_override_url: str | None = None


@lru_cache
def get_engine() -> Engine:
    return create_engine(
        _override_url or get_settings().database_url, pool_pre_ping=True, future=True
    )


@contextmanager
def use_database(url: str) -> Iterator[None]:
    """Temporarily point the process-wide engine at another database (eval/tests)."""
    global _override_url
    prev = _override_url
    reset_engine()
    _override_url = url
    try:
        yield
    finally:
        get_engine().dispose()
        reset_engine()
        _override_url = prev


def reset_engine() -> None:
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


@contextmanager
def session_scope() -> Iterator[Session]:
    s = get_sessionmaker()()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one session per request, committed on success."""
    with session_scope() as s:
        yield s
