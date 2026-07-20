"""Unit tests for auth refresh endpoint."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.unit


class TestAuthRefreshEndpoint:
    """Tests for auth refresh endpoint."""

    @pytest.mark.asyncio
    async def test_refresh_with_expired_token(self, async_client: AsyncClient):
        """Refresh with expired/invalid token should return 401."""
        response = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "expired.invalid.token"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_token_valid_structure(self, async_client: AsyncClient):
        """Refresh with valid JWT structure but wrong type should return 401."""
        # Create an access token and try to use it as refresh token
        from src.app.core.security import create_access_token

        access_token = create_access_token(subject="test-user-id")

        response = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": access_token},
        )
        assert response.status_code == 401


class TestAuthLoginEndpoint:
    """Tests for auth login endpoint."""

    @pytest.mark.asyncio
    async def test_login_invalid_username_format(self, async_client: AsyncClient):
        """Login with invalid username format should still return 401."""
        # FastAPI OAuth2PasswordRequestForm handles the data format
        response = await async_client.post(
            "/api/v1/auth/token",
            data={"username": "", "password": "pass"},
        )
        # Empty username might return 422 (validation) or 401
        assert response.status_code in [401, 422]

    @pytest.mark.asyncio
    async def test_login_missing_password(self, async_client: AsyncClient):
        """Login with missing password."""
        response = await async_client.post(
            "/api/v1/auth/token",
            data={"username": "testuser"},
        )
        assert response.status_code in [401, 422]


class TestSecurityModule:
    """Tests for security module functions."""

    def test_hash_password_function(self):
        """hash_password should return a hash."""
        from src.app.core.security import hash_password

        hashed = hash_password("TestPassword123!")
        assert hashed is not None
        assert hashed != "TestPassword123!"
        assert len(hashed) > 0

    def test_verify_password_correct(self):
        """verify_password should return True for correct password."""
        from src.app.core.security import hash_password, verify_password

        password = "TestPassword123!"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """verify_password should return False for incorrect password."""
        from src.app.core.security import hash_password, verify_password

        hashed = hash_password("CorrectPassword123!")
        assert verify_password("WrongPassword", hashed) is False

    def test_create_access_token_with_extra_claims(self):
        """create_access_token should include extra claims if provided."""
        import base64
        import json

        from src.app.core.security import create_access_token

        token = create_access_token(subject="test-user", extra_claims={"role": "admin", "scope": "read write"})

        # Decode payload (JWT format: header.payload.signature)
        parts = token.split(".")
        if len(parts) >= 2:
            payload = parts[1]
            # Add padding if needed
            padding = 4 - (len(payload) % 4)
            if padding != 4:
                payload += "=" * padding
            decoded = json.loads(base64.urlsafe_b64decode(payload))

            assert decoded["sub"] == "test-user"
            assert decoded["role"] == "admin"
            assert decoded["scope"] == "read write"

    def test_create_refresh_token(self):
        """create_refresh_token should create a valid refresh token."""
        from src.app.core.security import create_refresh_token

        token = create_refresh_token(subject="test-user-id")
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_token_invalid(self):
        """decode_token should raise for invalid token."""
        from jose import JWTError

        from src.app.core.security import decode_token

        with pytest.raises(JWTError):
            decode_token("not.valid.token")


class TestLoggingModule:
    """Tests for logging module."""

    def test_configure_logging(self):
        """configure_logging should run without error."""
        from src.app.core.logging import configure_logging

        # Should not raise
        configure_logging()

    def test_get_logger(self):
        """get_logger should return a logger."""
        from src.app.core.logging import get_logger

        logger = get_logger(__name__)
        assert logger is not None
        assert logger.name == __name__

    def test_logger_has_context(self):
        """Logger should have context filtering."""
        from src.app.core.logging import add_app_context, get_logger

        logger = get_logger("test")

        event_dict = {"event": "test_event"}
        result = add_app_context(logger, "info", event_dict)

        assert "app" in result
        assert "version" in result
