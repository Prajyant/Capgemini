"""Async PostgreSQL database connection."""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import settings


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


# FastAPI engine — single long-lived event loop, pooled connections are safe
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for use OUTSIDE the FastAPI request scope (Celery tasks, scripts).

    Creates a fresh engine with NullPool per call so connections never leak
    across event loops. Celery's `asyncio.run()` creates a new loop per task,
    and a shared pooled engine would bind connections to a closed loop and crash.
    """
    task_engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )
    SessionFactory = async_sessionmaker(
        task_engine, class_=AsyncSession, expire_on_commit=False
    )
    try:
        async with SessionFactory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    finally:
        await task_engine.dispose()


async def init_db() -> None:
    """Create all tables. Use Alembic in production."""
    # Import models so they register with Base.metadata
    from app.models import (  # noqa: F401
        lead, company, sequence, email_event, agent_decision, ab_test
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
