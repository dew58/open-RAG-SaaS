"""
Async SQLAlchemy database configuration.

Architecture Decisions:
- asyncpg driver: significantly faster than psycopg2 for async workloads
- Connection pooling: sized for concurrent production load
- Session-per-request pattern via dependency injection
- Separate sync engine for Alembic migrations (Alembic doesn't support async)
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.core.config import settings


class Base(DeclarativeBase):
    """
    Shared declarative base for all ORM models.
    All models import from here to ensure they're registered with the same metadata.
    """
    pass


def build_engine() -> AsyncEngine:
    """
    Build the async engine with production-tuned pool settings.

    Pool sizing formula: (num_cores * 2) + effective_spindle_count
    For a 4-core server: pool_size=20, max_overflow=40 gives headroom for spikes.

    NullPool is used in worker processes to prevent connection sharing across forks.
    In production with multiple Gunicorn workers, each worker maintains its own pool.
    """
    connect_args = {
        "server_settings": {
            "application_name": "rag_saas",
            "jit": "off",  # Disable JIT for short-running OLTP queries
        },
        "command_timeout": 60,
    }

    return create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,  # Log SQL only in debug mode
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_recycle=settings.DB_POOL_RECYCLE,
        pool_pre_ping=True,  # Verify connection health before checkout
        connect_args=connect_args,
    )


engine = build_engine()

# async_sessionmaker is the v2 replacement for sessionmaker
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Prevent lazy-load errors after commit in async context
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a scoped database session.

    Pattern: one session per request, committed on success, rolled back on error.
    The session is always closed in the finally block.

    Usage:
        @router.get("/items")
        async def list_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db_transaction() -> AsyncGenerator[AsyncSession, None]:
    """
    Provides a session with explicit transaction control.
    Use this for operations that require atomic multi-step writes.
    """
    async with AsyncSessionLocal() as session:
        async with session.begin():
            yield session
