"""Shared test fixtures and configuration."""

import asyncio
from collections.abc import AsyncGenerator
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.app.core.config import Settings, get_settings
from src.app.core.security import create_access_token, hash_password
from src.app.db.session import Base, get_db
from src.app.main import app
from src.app.models.models import Item, User

# ── Test settings ─────────────────────────────────────────────────────────────
TEST_DATABASE_URL = "postgresql+asyncpg://test_user:test_password@localhost:5432/test_db"
TEST_REDIS_URL = "redis://localhost:6379/0"


def get_test_settings() -> Settings:
    """Override settings for tests."""
    return Settings(
        environment="testing",
        database_url=TEST_DATABASE_URL,
        redis_url=TEST_REDIS_URL,
        secret_key="test-secret-key-that-is-long-enough-for-hs256",
        debug=True,
    )


# ── Engine & session fixtures ─────────────────────────────────────────────────

# Module-level engine (singleton for test session)
_engine = None


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine(event_loop):
    """Create a test database engine for the test session."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            TEST_DATABASE_URL,
            future=True,
            echo=False,
            pool_pre_ping=True,
        )

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield _engine

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await _engine.dispose()
    _engine = None


@pytest_asyncio.fixture
async def db_session(test_engine, event_loop) -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional test database session that rolls back after each test."""
    factory = async_sessionmaker(
        bind=test_engine,
        expire_on_commit=False,
        autoflush=False,
    )

    async with factory() as session:
        async with session.begin():
            yield session
            await session.rollback()


# ── App / HTTP client fixtures ─────────────────────────────────────────────────


@pytest.fixture
def settings_override():
    """Patch get_settings to return test settings."""
    with patch("src.app.core.config.get_settings", return_value=get_test_settings()):
        yield


@pytest_asyncio.fixture
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client with DB session override and mocked Redis."""
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_settings] = get_test_settings

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


# ── Data factory fixtures ─────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create and persist a regular test user."""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=hash_password("TestPassword123!"),
        full_name="Test User",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_superuser(db_session: AsyncSession) -> User:
    """Create and persist a superuser."""
    user = User(
        username="admin",
        email="admin@example.com",
        hashed_password=hash_password("AdminPassword123!"),
        full_name="Admin User",
        is_active=True,
        is_superuser=True,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_item(db_session: AsyncSession, test_user: User) -> Item:
    """Create and persist a test item."""
    item = Item(
        title="Test Item",
        description="A test item description",
        is_public=False,
        owner_id=test_user.id,
    )
    db_session.add(item)
    await db_session.flush()
    await db_session.refresh(item)
    return item


@pytest.fixture
def user_token(test_user: User) -> str:
    """Generate a valid access token for the test user."""
    return create_access_token(subject=str(test_user.id))


@pytest.fixture
def superuser_token(test_superuser: User) -> str:
    """Generate a valid access token for the superuser."""
    return create_access_token(subject=str(test_superuser.id))


@pytest.fixture
def auth_headers(user_token: str) -> dict[str, str]:
    """Return Authorization headers for the regular test user."""
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture
def superuser_headers(superuser_token: str) -> dict[str, str]:
    """Return Authorization headers for the superuser."""
    return {"Authorization": f"Bearer {superuser_token}"}
