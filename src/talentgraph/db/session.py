"""Async SQLAlchemy engine and session factory.

Create one engine per process: the API creates it in the FastAPI lifespan (batch BackgroundTasks
reuse it). Never share an async engine across a fork.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from talentgraph.config import get_settings

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None
_db_available: bool = False


def is_db_available() -> bool:
    """Return whether the database backend is active and reachable."""
    return _db_available and _sessionmaker is not None


def set_db_available(available: bool) -> None:
    """Explicitly set the database backend availability state."""
    global _db_available
    _db_available = available


def init_engine(url: str | None = None) -> AsyncEngine:
    global _engine, _sessionmaker, _db_available
    _engine = create_async_engine(url or get_settings().database_url, pool_pre_ping=True)
    _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)
    _db_available = True
    return _engine


def get_engine() -> AsyncEngine:
    return _engine or init_engine()


async def dispose_engine() -> None:
    global _engine, _sessionmaker, _db_available
    if _engine is not None:
        await _engine.dispose()
    _engine, _sessionmaker = None, None
    _db_available = False


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency."""
    if not is_db_available():
        raise ConnectionError("Database is offline (in-memory fallback active)")
    if _sessionmaker is None:
        init_engine()
    assert _sessionmaker is not None
    async with _sessionmaker() as session:
        yield session


@asynccontextmanager
async def async_session_scope() -> AsyncIterator[AsyncSession]:
    """Context manager for background tasks and offline operations."""
    if not is_db_available():
        raise ConnectionError("Database is offline (in-memory fallback active)")
    if _sessionmaker is None:
        init_engine()
    assert _sessionmaker is not None
    async with _sessionmaker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
