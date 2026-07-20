"""Unit tests for application configuration."""

import pytest

from src.app.core.config import Settings, get_settings


class TestSettings:
    """Tests for Settings model validation."""

    def test_default_environment_is_development(self):
        """Default environment should be 'development' when no env var set."""
        import os

        # Temporarily remove ENVIRONMENT to test the actual default
        env_backup = os.environ.pop("ENVIRONMENT", None)
        try:
            s = Settings(secret_key="a" * 32)
            assert s.environment == "development"
        finally:
            if env_backup:
                os.environ["ENVIRONMENT"] = env_backup

    def test_is_production_flag(self):
        """is_production returns True only in production."""
        s = Settings(environment="production", secret_key="a" * 32)
        assert s.is_production is True
        s2 = Settings(environment="staging", secret_key="a" * 32)
        assert s2.is_production is False

    def test_is_testing_flag(self):
        """is_testing returns True only in testing."""
        s = Settings(environment="testing", secret_key="a" * 32)
        assert s.is_testing is True

    def test_invalid_environment_raises(self):
        """An invalid environment string should raise a ValidationError."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Settings(environment="invalid_env", secret_key="a" * 32)

    def test_port_bounds(self):
        """Port must be within valid TCP range."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Settings(secret_key="a" * 32, port=0)
        with pytest.raises(ValidationError):
            Settings(secret_key="a" * 32, port=70000)

    def test_empty_database_url_raises(self):
        """Empty DATABASE_URL should raise a validation error."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Settings(secret_key="a" * 32, database_url="")

    def test_get_settings_returns_same_instance(self):
        """get_settings should return the same cached instance each time."""
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_cache_ttl_default(self):
        """Default cache TTL should be 300 seconds."""
        s = Settings(secret_key="a" * 32)
        assert s.cache_ttl == 300

    def test_jwt_algorithm_default(self):
        """Default JWT algorithm should be HS256."""
        s = Settings(secret_key="a" * 32)
        assert s.jwt_algorithm == "HS256"
