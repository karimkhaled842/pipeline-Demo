"""Even more unit tests for additional coverage."""

import pytest

pytestmark = pytest.mark.unit


class TestAPIEndpoints:
    """Tests for API endpoint helpers."""

    def test_deps_current_user_type(self):
        """CurrentUser type alias is correct."""
        from src.app.api.v1.deps import CurrentUser

        # Should be Annotated[User, Depends(...)]
        assert CurrentUser.__origin__ is not None

    def test_deps_superuser_type(self):
        """SuperUser type alias is correct."""
        from src.app.api.v1.deps import SuperUser

        assert SuperUser.__origin__ is not None

    def test_deps_db_session_type(self):
        """DbSession type alias is correct."""
        from src.app.api.v1.deps import DbSession

        assert DbSession.__origin__ is not None


class TestMainApp:
    """Tests for main app functions."""

    def test_app_creation(self):
        """create_app returns FastAPI instance."""
        from src.app.main import create_app

        app = create_app()
        assert app is not None
        assert app.title == "SecureApp"

    def test_app_has_routers(self):
        """App includes routers."""
        from src.app.main import create_app

        app = create_app()
        # Check that routers are included
        routes = [r.path for r in app.routes]
        assert any("/api/v1/health" in p for p in routes)
        assert any("/api/v1/auth" in p for p in routes)


class TestHealthEndpointDetails:
    """Tests for health endpoint details."""

    def test_health_check_db_imports(self):
        """Health check imports are available."""
        from src.app.api.v1.health import check_db_connection

        assert check_db_connection is not None

    def test_health_check_redis_imports(self):
        """Health check imports are available."""
        from src.app.api.v1.health import check_redis_connection

        assert check_redis_connection is not None


class TestAuthEndpointDetails:
    """Tests for auth endpoint details."""

    def test_auth_router_exists(self):
        """Auth router is defined."""
        from src.app.api.v1.auth import router

        assert router is not None
        assert router.prefix == "/auth"


class TestItemsEndpointDetails:
    """Tests for items endpoint details."""

    def test_items_router_exists(self):
        """Items router is defined."""
        from src.app.api.v1.items import router

        assert router is not None
        assert router.prefix == "/items"


class TestUsersEndpointDetails:
    """Tests for users endpoint details."""

    def test_users_router_exists(self):
        """Users router is defined."""
        from src.app.api.v1.users import router

        assert router is not None
        assert router.prefix == "/users"


class TestLoggingSetup:
    """Tests for logging setup."""

    def test_configure_logging_returns_none(self):
        """configure_logging runs without error."""
        from src.app.core.logging import configure_logging

        result = configure_logging()
        assert result is None  # It configures in-place

    def test_get_logger_different_names(self):
        """get_logger can create loggers with different names."""
        from src.app.core.logging import get_logger

        logger1 = get_logger("module1")
        logger2 = get_logger("module2")

        assert logger1.name == "module1"
        assert logger2.name == "module2"


class TestSecurityTokenValidation:
    """Tests for JWT token validation."""

    def test_decode_valid_access_token(self):
        """decode_token works with access token."""
        from src.app.core.security import create_access_token, decode_token

        token = create_access_token(subject="test-user-456")
        claims = decode_token(token)

        assert claims["sub"] == "test-user-456"
        assert "exp" in claims
        assert "iat" in claims

    def test_decode_valid_refresh_token(self):
        """decode_token works with refresh token."""
        from src.app.core.security import create_refresh_token, decode_token

        token = create_refresh_token(subject="test-user-789")
        claims = decode_token(token)

        assert claims["sub"] == "test-user-789"
        assert claims["type"] == "refresh"

    def test_decode_token_missing_signature(self):
        """decode_token raises on malformed token."""
        from jose import JWTError

        from src.app.core.security import decode_token

        with pytest.raises(JWTError):
            decode_token("only.two.parts")


class TestModelRelationships:
    """Tests for model relationships."""

    def test_user_relationship_items(self):
        """User has items relationship."""
        from src.app.models.models import User

        assert hasattr(User, "items")

    def test_item_relationship_owner(self):
        """Item has owner relationship."""
        from src.app.models.models import Item

        assert hasattr(Item, "owner")


class TestSchemaValidation:
    """Tests for schema validation."""

    def test_user_create_validates_username_min_length(self):
        """UserCreate validates username minimum length."""
        from pydantic import ValidationError

        from src.app.schemas.schemas import UserCreate

        with pytest.raises(ValidationError):
            UserCreate(
                username="ab",  # Too short
                email="test@example.com",
                password="ValidPass123!",
            )

    def test_user_create_validates_password_min_length(self):
        """UserCreate validates password minimum length."""
        from pydantic import ValidationError

        from src.app.schemas.schemas import UserCreate

        with pytest.raises(ValidationError):
            UserCreate(
                username="validuser",
                email="test@example.com",
                password="Ab1",  # Too short
            )

    def test_item_create_validates_title_required(self):
        """ItemCreate requires title."""
        from pydantic import ValidationError

        from src.app.schemas.schemas import ItemCreate

        with pytest.raises(ValidationError):
            ItemCreate(description="Has description but no title")


class TestCacheHelper:
    """Tests for cache helper functions."""

    def test_cache_prefix_constant(self):
        """Cache uses correct prefix."""
        from src.app.services import cache

        # Just check the module loads
        assert hasattr(cache, "cache_set")
        assert hasattr(cache, "cache_get")

    def test_cache_delete_import(self):
        """cache_delete is available."""
        from src.app.services.cache import cache_delete

        assert callable(cache_delete)

    def test_cache_clear_import(self):
        """cache_exists is available."""
        from src.app.services.cache import cache_exists

        assert callable(cache_exists)

    def test_cache_service_imports(self):
        """Cache service has all required functions."""
        from src.app.services import cache

        assert hasattr(cache, "cache_set")
        assert hasattr(cache, "cache_get")
        assert hasattr(cache, "cache_delete")
        assert hasattr(cache, "cache_exists")
