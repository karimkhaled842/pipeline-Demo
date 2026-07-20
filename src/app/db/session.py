"""SQLAlchemy async engine and session factory."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from src.app.core.config import get_settings
from src.app.core.logging import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def _make_engine(database_url: str | None = None) -> AsyncEngine:
    """Build an async SQLAlchemy engine."""
    settings = get_settings()
    url = database_url or settings.database_url
    # asyncpg requires postgresql+asyncpg:// scheme
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    return create_async_engine(
        url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        pool_pre_ping=True,
        echo=settings.db_echo,
        future=True,
    )


_engine = None
_session_factory = None


def get_engine() -> AsyncEngine | None:
    """Return the singleton async engine."""
    global _engine
    if _engine is None:
        _engine = _make_engine()
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession] | None:
    """Return the singleton async session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a database session per request."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables() -> None:
    """Create all database tables (for dev/testing; use Alembic for production)."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("database_tables_created")


async def drop_tables() -> None:
    """Drop all database tables (testing only)."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    logger.info("database_tables_dropped")


async def check_db_connection() -> bool:
    """Return True if the database is reachable."""
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            from sqlalchemy import text

            await conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.error("db_connection_failed", error=str(exc))
        return False
