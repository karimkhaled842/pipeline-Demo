"""Unit tests for data schemas."""

import uuid
from datetime import UTC, datetime

import pytest

from src.app.schemas.schemas import (
    ComponentHealth,
    HealthResponse,
    ItemCreate,
    ItemResponse,
    PaginatedResponse,
    Token,
    UserCreate,
    UserResponse,
    UserUpdate,
)

pytestmark = pytest.mark.unit


class TestTokenSchema:
    """Tests for Token schema."""

    def test_token_creation(self):
        """Token schema can be created with tokens."""

        token = Token(access_token="access_token_value", refresh_token="refresh_token_value", token_type="bearer")

        assert token.access_token == "access_token_value"
        assert token.refresh_token == "refresh_token_value"
        assert token.token_type == "bearer"

    def test_token_default_token_type(self):
        """Token should have default token_type of bearer."""
        token = Token(access_token="access", refresh_token="refresh")
        assert token.token_type == "bearer"


class TestUserCreateSchema:
    """Tests for UserCreate schema."""

    def test_user_create_valid_data(self):
        """UserCreate accepts valid data."""
        from src.app.schemas.schemas import UserCreate

        user = UserCreate(username="newuser", email="newuser@example.com", password="SecurePass123!")

        assert user.username == "newuser"
        assert user.email == "newuser@example.com"
        assert user.password == "SecurePass123!"

    def test_user_create_email_validation(self):
        """UserCreate validates email format."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            UserCreate(username="user", email="invalid-email", password="Password123")


class TestUserUpdateSchema:
    """Tests for UserUpdate schema."""

    def test_user_update_partial(self):
        """UserUpdate allows partial updates."""

        update = UserUpdate(full_name="New Name")
        assert update.full_name == "New Name"
        assert update.email is None
        assert update.password is None


class TestUserResponseSchema:
    """Tests for UserResponse schema."""

    def test_user_response_from_dict(self):
        """UserResponse can be created from dict."""

        data = {
            "id": uuid.uuid4(),
            "username": "testuser",
            "email": "test@example.com",
            "full_name": "Test User",
            "is_active": True,
            "is_superuser": False,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }

        user = UserResponse.model_validate(data)
        assert user.username == "testuser"
        assert user.email == "test@example.com"


class TestItemCreateSchema:
    """Tests for ItemCreate schema."""

    def test_item_create_all_fields(self):
        """ItemCreate accepts all fields."""
        from src.app.schemas.schemas import ItemCreate

        item = ItemCreate(title="My Item", description="Item Description", is_public=True)

        assert item.title == "My Item"
        assert item.description == "Item Description"
        assert item.is_public is True

    def test_item_create_default_is_public(self):
        """ItemCreate defaults is_public to False."""
        item = ItemCreate(title="Private Item")
        assert item.is_public is False


class TestItemResponseSchema:
    """Tests for ItemResponse schema."""

    def test_item_response_from_dict(self):
        """ItemResponse can be created from dict."""

        data = {
            "id": 1,
            "title": "Test Item",
            "description": "Description",
            "is_public": False,
            "owner_id": uuid.uuid4(),
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }

        item = ItemResponse.model_validate(data)
        assert item.title == "Test Item"


class TestHealthResponseSchema:
    """Tests for HealthResponse schema."""

    def test_health_response_structure(self):
        """HealthResponse has correct structure."""

        health = HealthResponse(
            status="healthy",
            version="1.0.0",
            environment="testing",
            components={
                "database": ComponentHealth(status="healthy", message=None),
                "redis": ComponentHealth(status="healthy", message=None),
            },
        )

        assert health.status == "healthy"
        assert health.version == "1.0.0"
        assert "database" in health.components
        assert "redis" in health.components


class TestPaginatedResponseSchema:
    """Tests for PaginatedResponse schema."""

    def test_paginated_response_creation(self):
        """PaginatedResponse can be created."""

        users = [
            UserResponse(
                id=uuid.uuid4(),
                username="user1",
                email="user1@example.com",
                full_name="User 1",
                is_active=True,
                is_superuser=False,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        ]

        response = PaginatedResponse(total=1, page=1, page_size=20, items=users)

        assert response.total == 1
        assert response.page == 1
        assert response.page_size == 20
        assert len(response.items) == 1
