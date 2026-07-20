"""Unit tests for data models."""

import uuid

import pytest

pytestmark = pytest.mark.unit


class TestUserModel:
    """Tests for User model."""

    def test_user_model_creation(self):
        """User model can be created with all fields."""
        from src.app.models.models import User

        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
            full_name="Test User",
            is_active=True,
            is_superuser=False,
        )

        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.is_active is True
        assert user.is_superuser is False

    def test_user_model_tablename(self):
        """User model should have correct tablename."""
        from src.app.models.models import User

        assert User.__tablename__ == "users"

    def test_user_model_has_timestamps(self):
        """User model should have created_at and updated_at."""
        from src.app.models.models import User

        assert hasattr(User, "created_at")
        assert hasattr(User, "updated_at")


class TestItemModel:
    """Tests for Item model."""

    def test_item_model_creation(self):
        """Item model can be created with all fields."""
        from src.app.models.models import Item

        owner_id = uuid.uuid4()
        item = Item(
            title="Test Item",
            description="Test Description",
            is_public=False,
            owner_id=owner_id,
        )

        assert item.title == "Test Item"
        assert item.description == "Test Description"
        assert item.is_public is False
        assert item.owner_id == owner_id

    def test_item_model_tablename(self):
        """Item model should have correct tablename."""
        from src.app.models.models import Item

        assert Item.__tablename__ == "items"


class TestTimestampMixin:
    """Tests for TimestampMixin."""

    def test_timestamp_mixin_fields(self):
        """TimestampMixin should add created_at and updated_at."""
        from src.app.models.models import TimestampMixin

        assert hasattr(TimestampMixin, "created_at")
        assert hasattr(TimestampMixin, "updated_at")
