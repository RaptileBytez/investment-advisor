"""SQLAlchemy engine, session factory, and FastAPI dependency."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def _ensure_sqlite_dir(url: str) -> None:
    """Create the parent dir for SQLite file URLs so connect() doesn't fail."""
    if url.startswith("sqlite:///"):
        path = Path(url.removeprefix("sqlite:///"))
        path.parent.mkdir(parents=True, exist_ok=True)


_settings = get_settings()
_ensure_sqlite_dir(_settings.database_url)

engine = create_engine(
    _settings.database_url,
    # check_same_thread is only needed for SQLite + threaded FastAPI workers.
    connect_args={"check_same_thread": False} if _settings.database_url.startswith("sqlite") else {},
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    class_=Session,
)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: yield a session and ensure it's closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
