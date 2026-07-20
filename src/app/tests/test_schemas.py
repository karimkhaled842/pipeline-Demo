"""Unit tests for Pydantic schemas validation."""

import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.app.schemas.schemas import (
    ItemCreate,
    Token,
    UserCreate,
    UserResponse,
    UserUpdate,
)


class TestUserCreateSchema:
    """Validation rules for UserCreate."""

    def test_valid_user_create(self):
        """A fully valid UserCreate should parse without errors."""
        u = UserCreate(
            username="john_doe",
            email="john@example.com",
            password="SecurePass123!",
        )
        assert u.username == "john_doe"

    def test_username_too_short(self):
        """Username shorter than 3 characters should fail."""
        with pytest.raises(ValidationError):
            UserCreate(username="ab", email="x@x.com", password="SecurePass!")

    def test_username_too_long(self):
        """Username longer than 50 characters should fail."""
        with pytest.raises(ValidationError):
            UserCreate(username="a" * 51, email="x@x.com", password="SecurePass!")

    def test_invalid_email(self):
        """Invalid email format should fail."""
        with pytest.raises(ValidationError):
            UserCreate(username="john", email="not-an-email", password="SecurePass!")

    def test_password_too_short(self):
        """Password shorter than 8 characters should fail."""
        with pytest.raises(ValidationError):
            UserCreate(username="john", email="j@example.com", password="short")

    def test_full_name_optional(self):
        """full_name is optional and defaults to None."""
        u = UserCreate(username="john", email="j@example.com", password="SecurePass!")
        assert u.full_name is None


class TestUserUpdateSchema:
    """Validation rules for UserUpdate (all fields optional)."""

    def test_empty_update_is_valid(self):
        """An update with no fields is acceptable."""
        u = UserUpdate()
        assert u.model_dump(exclude_none=True) == {}

    def test_partial_update(self):
        """Only provided fields should be set."""
        u = UserUpdate(full_name="New Name")
        assert u.full_name == "New Name"
        assert u.email is None


class TestItemCreateSchema:
    """Validation rules for ItemCreate."""

    def test_valid_item(self):
        """A valid ItemCreate should parse correctly."""
        item = ItemCreate(title="My Item", description="Details", is_public=True)
        assert item.title == "My Item"
        assert item.is_public is True

    def test_title_required(self):
        """Title is required and must be non-empty."""
        with pytest.raises(ValidationError):
            ItemCreate(title="")

    def test_description_optional(self):
        """Description is optional."""
        item = ItemCreate(title="Item")
        assert item.description is None

    def test_is_public_defaults_to_false(self):
        """is_public should default to False."""
        item = ItemCreate(title="Item")
        assert item.is_public is False


class TestTokenSchema:
    """Token schema structure."""

    def test_token_defaults_to_bearer(self):
        """token_type should default to 'bearer'."""
        t = Token(access_token="aaa", refresh_token="bbb")
        assert t.token_type == "bearer"

    def test_token_fields_present(self):
        """Both access and refresh tokens must be present."""
        t = Token(access_token="access123", refresh_token="refresh456")
        assert t.access_token == "access123"
        assert t.refresh_token == "refresh456"


class TestUserResponseSchema:
    """UserResponse ORM serialisation."""

    def test_from_attributes(self):
        """UserResponse should be buildable from a dict (model_validate)."""
        now = datetime.now(UTC)
        data = {
            "id": uuid.uuid4(),
            "username": "alice",
            "email": "alice@example.com",
            "full_name": "Alice",
            "is_active": True,
            "is_superuser": False,
            "created_at": now,
            "updated_at": now,
        }
        resp = UserResponse.model_validate(data)
        assert resp.username == "alice"
        assert resp.is_active is True
