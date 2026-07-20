"""Additional unit tests for schemas and helpers."""

import uuid

import pytest

pytestmark = pytest.mark.unit


class TestErrorDetailSchema:
    """Tests for ErrorDetail schema."""

    def test_error_detail_creation(self):
        """ErrorDetail can be created with code and message."""
        from src.app.schemas.schemas import ErrorDetail

        error = ErrorDetail(code="INVALID_INPUT", message="Invalid data")
        assert error.code == "INVALID_INPUT"
        assert error.message == "Invalid data"

    def test_error_detail_with_extra(self):
        """ErrorDetail can include extra fields."""
        from src.app.schemas.schemas import ErrorDetail

        error = ErrorDetail(code="INVALID_FIELD", message="Field is required")
        assert error.code == "INVALID_FIELD"


class TestTokenDataSchema:
    """Tests for TokenData schema."""

    def test_token_data_creation(self):
        """TokenData can be created with sub and type."""
        from src.app.schemas.schemas import TokenData

        token = TokenData(sub="user-123", type="access")
        assert token.sub == "user-123"
        assert token.type == "access"


class TestItemUpdateSchema:
    """Tests for ItemUpdate schema."""

    def test_item_update_all_fields(self):
        """ItemUpdate can update all fields."""
        from src.app.schemas.schemas import ItemUpdate

        update = ItemUpdate(title="New Title", description="New Description", is_public=True)
        assert update.title == "New Title"
        assert update.description == "New Description"
        assert update.is_public is True

    def test_item_update_partial_fields(self):
        """ItemUpdate can update only specific fields."""
        from src.app.schemas.schemas import ItemUpdate

        update = ItemUpdate(title="Only Title")
        assert update.title == "Only Title"
        assert update.description is None
        assert update.is_public is None


class TestUserUpdateSchema:
    """Tests for UserUpdate schema."""

    def test_user_update_all_fields(self):
        """UserUpdate can update all fields."""
        from src.app.schemas.schemas import UserUpdate

        update = UserUpdate(email="new@example.com", full_name="New Name", password="newpassword123")
        assert update.email == "new@example.com"
        assert update.full_name == "New Name"
        assert update.password == "newpassword123"


class TestComponentHealthSchema:
    """Tests for ComponentHealth schema."""

    def test_component_healthy(self):
        """ComponentHealth can represent healthy component."""
        from src.app.schemas.schemas import ComponentHealth

        comp = ComponentHealth(status="healthy")
        assert comp.status == "healthy"

    def test_component_unhealthy(self):
        """ComponentHealth can represent unhealthy."""
        from src.app.schemas.schemas import ComponentHealth

        comp = ComponentHealth(status="unhealthy")
        assert comp.status == "unhealthy"


class TestPaginationParams:
    """Tests for PaginationParams."""

    def test_pagination_skip_calculation(self):
        """PaginationParams calculates skip correctly."""
        from src.app.api.v1.deps import PaginationParams

        p = PaginationParams(page=3, page_size=10)
        assert p.skip == 20  # (3-1) * 10

    def test_pagination_limit(self):
        """PaginationParams returns limit."""
        from src.app.api.v1.deps import PaginationParams

        p = PaginationParams(page=1, page_size=25)
        assert p.limit == 25


class TestCacheKeys:
    """Tests for cache key generation."""

    def test_user_service_cache_key_format(self):
        """User service cache key format is correct."""
        from src.app.services.user_service import _cache_key

        user_id = uuid.uuid4()
        key = _cache_key(user_id)
        assert key.startswith("user:")
        assert str(user_id) in key


class TestSecurityHelpers:
    """Tests for security helper functions."""

    def test_hash_password_returns_string(self):
        """hash_password returns a bcrypt hash string."""
        from src.app.core.security import hash_password

        result = hash_password("testpass123")
        assert isinstance(result, str)
        assert result.startswith("$2b$")  # bcrypt prefix

    def test_verify_password_accepts_correct(self):
        """verify_password returns True for correct password."""
        from src.app.core.security import hash_password, verify_password

        password = "MySecurePass123!"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_rejects_incorrect(self):
        """verify_password returns False for incorrect password."""
        from src.app.core.security import hash_password, verify_password

        hashed = hash_password("CorrectPass123!")
        assert verify_password("WrongPass456!", hashed) is False

    def test_create_access_token_returns_jwt(self):
        """create_access_token returns a JWT string."""
        from src.app.core.security import create_access_token

        token = create_access_token(subject="user-123")
        assert isinstance(token, str)
        assert len(token.split(".")) == 3  # JWT has 3 parts

    def test_create_refresh_token_returns_jwt(self):
        """create_refresh_token returns a JWT string."""
        from src.app.core.security import create_refresh_token

        token = create_refresh_token(subject="user-123")
        assert isinstance(token, str)
        assert len(token.split(".")) == 3

    def test_decode_token_with_valid_token(self):
        """decode_token works with valid token."""
        from src.app.core.security import create_access_token, decode_token

        token = create_access_token(subject="user-123")
        claims = decode_token(token)
        assert claims["sub"] == "user-123"
        assert claims["type"] == "access"

    def test_decode_token_with_invalid_token(self):
        """decode_token raises error with invalid token."""
        from jose import JWTError

        from src.app.core.security import decode_token

        with pytest.raises(JWTError):
            decode_token("invalid.token.here")


class TestConfigDefaults:
    """Tests for config default values."""

    def test_default_database_url(self):
        """Settings has default database URL."""
        from src.app.core.config import Settings

        s = Settings(secret_key="a" * 32)
        assert s.database_url is not None
        assert "postgresql" in s.database_url

    def test_default_redis_url(self):
        """Settings has default Redis URL."""
        from src.app.core.config import Settings

        s = Settings(secret_key="a" * 32)
        assert s.redis_url is not None
        assert "redis" in s.redis_url

    def test_default_jwt_algorithm(self):
        """Settings has default JWT algorithm."""
        from src.app.core.config import Settings

        s = Settings(secret_key="a" * 32)
        assert s.jwt_algorithm == "HS256"

    def test_default_rate_limiting(self):
        """Settings has default rate limiting values."""
        from src.app.core.config import Settings

        s = Settings(secret_key="a" * 32)
        assert s.rate_limit_requests == 100
        assert s.rate_limit_window == 60
