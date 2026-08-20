"""Engine + session factory. SQLite gets WAL mode + busy_timeout so the
supervisor daemon and a run worker can touch the DB concurrently without
"database is locked" errors. Postgres works unmodified via DOJO_DATABASE_URL.
"""

from __future__ import annotations

from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from research_dojo.config.settings import get_settings


def _enable_sqlite_wal(dbapi_conn, _record) -> None:
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def make_engine(database_url: str | None = None) -> Engine:
    url = database_url or get_settings().resolve_database_url()
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    engine = create_engine(url, connect_args=connect_args, future=True)
    if url.startswith("sqlite"):
        event.listen(engine, "connect", _enable_sqlite_wal)
    return engine


@lru_cache
def get_engine() -> Engine:
    return make_engine()


@lru_cache
def get_session_factory() -> sessionmaker:
    return sessionmaker(bind=get_engine(), expire_on_commit=False, future=True)


def new_session() -> Session:
    return get_session_factory()()


@contextmanager
def session_scope():
    """Transactional scope: commits on success, rolls back on exception."""
    session = new_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def reset_engine_cache() -> None:
    """Test helper: clear cached engine/sessionmaker so a new DB URL takes effect."""
    get_engine.cache_clear()
    get_session_factory.cache_clear()
