"""More unit tests for service layer coverage."""

import uuid

import pytest

pytestmark = pytest.mark.unit


class TestUserServiceFunctions:
    """Tests for user service function coverage."""

    def test_get_user_by_id_cache_key(self):
        """_cache_key generates correct key."""
        from src.app.services.user_service import _cache_key

        test_id = uuid.UUID("12345678-1234-5678-1234-567812345678")
        key = _cache_key(test_id)
        assert key == "user:12345678-1234-5678-1234-567812345678"

    def test_authenticate_user_exists(self):
        """authenticate_user function exists."""
        from src.app.services import user_service

        assert hasattr(user_service, "authenticate_user")


class TestCacheServiceFunctions:
    """Tests for cache service function coverage."""

    def test_cache_key_prefix_constant(self):
        """Cache uses correct prefix."""
        from src.app.services.user_service import _CACHE_PREFIX, _CACHE_TTL

        assert _CACHE_PREFIX == "user"
        assert _CACHE_TTL == 300


class TestDbSessionFunctions:
    """Tests for database session functions."""

    def test_get_db_type(self):
        """get_db returns async generator."""
        import inspect

        from src.app.db.session import get_db

        assert inspect.isasyncgenfunction(get_db)

    def test_session_module_imports(self):
        """Session module has expected components."""
        from src.app.db import session

        assert hasattr(session, "get_db")
        assert hasattr(session, "Base")

    def test_schema_module_imports(self):
        """Schema module has expected components."""
        from src.app.schemas import schemas

        assert hasattr(schemas, "UserCreate")
        assert hasattr(schemas, "UserResponse")
        assert hasattr(schemas, "ItemCreate")
        assert hasattr(schemas, "ItemResponse")
        assert hasattr(schemas, "Token")
        assert hasattr(schemas, "HealthResponse")


class TestModelsDetailed:
    """Tests for model detailed coverage."""

    def test_user_model_fields(self):
        """User model has expected fields."""
        from src.app.models.models import User

        user = User(username="testuser", email="test@example.com", hashed_password="hash", full_name="Test User")

        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.hashed_password == "hash"
        assert user.full_name == "Test User"

    def test_item_model_fields(self):
        """Item model has expected fields."""
        from src.app.models.models import Item

        owner_id = uuid.uuid4()
        item = Item(title="Test Item", description="Description", owner_id=owner_id)

        assert item.title == "Test Item"
        assert item.description == "Description"
        assert item.owner_id == owner_id
