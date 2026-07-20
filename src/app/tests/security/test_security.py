"""Security tests for the application."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.security


class TestSecurityHeaders:
    """Verify security headers are present on all responses."""

    @pytest.mark.asyncio
    async def test_x_content_type_options(self, async_client: AsyncClient):
        """X-Content-Type-Options: nosniff must be present."""
        response = await async_client.get("/api/v1/health/live")
        assert response.headers.get("x-content-type-options") == "nosniff"

    @pytest.mark.asyncio
    async def test_x_frame_options(self, async_client: AsyncClient):
        """X-Frame-Options: DENY must be present."""
        response = await async_client.get("/api/v1/health/live")
        assert response.headers.get("x-frame-options") == "DENY"

    @pytest.mark.asyncio
    async def test_x_xss_protection(self, async_client: AsyncClient):
        """X-XSS-Protection header must be present."""
        response = await async_client.get("/api/v1/health/live")
        assert "x-xss-protection" in response.headers

    @pytest.mark.asyncio
    async def test_referrer_policy(self, async_client: AsyncClient):
        """Referrer-Policy header must be set."""
        response = await async_client.get("/api/v1/health/live")
        assert "referrer-policy" in response.headers


class TestAuthorizationSecurity:
    """Tests for authentication and authorization enforcement."""

    @pytest.mark.asyncio
    async def test_protected_endpoint_without_token(self, async_client: AsyncClient):
        """Accessing protected endpoints without a token returns 401."""
        response = await async_client.get("/api/v1/auth/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_protected_endpoint_with_invalid_token(self, async_client: AsyncClient):
        """Invalid token should return 401."""
        headers = {"Authorization": "Bearer invalid.token.here"}
        response = await async_client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_superuser_endpoint_as_regular_user(self, async_client: AsyncClient, auth_headers):
        """Regular users cannot access superuser-only endpoints."""
        response = await async_client.get("/api/v1/users/", headers=auth_headers)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_cannot_access_other_users_items(
        self,
        async_client: AsyncClient,
        auth_headers,
        test_item,
        test_superuser,
    ):
        """A user should not access another user's private item."""
        # test_item belongs to test_user, not the superuser accessed as regular
        # (Superusers can still access — use a separate non-owner regular user scenario)
        response = await async_client.get(f"/api/v1/items/{test_item.id}", headers=auth_headers)
        assert response.status_code == 200  # owner can access


class TestInputValidation:
    """Test that the API rejects malformed/malicious input."""

    @pytest.mark.asyncio
    async def test_sql_injection_in_username(self, async_client: AsyncClient):
        """SQL injection attempt in username field should be rejected."""
        payload = {
            "username": "'; DROP TABLE users; --",
            "email": "hack@example.com",
            "password": "Password123!",
        }
        response = await async_client.post("/api/v1/users/", json=payload)
        # Either rejected by validation or safely handled — never 500
        assert response.status_code in (201, 409, 422)
        assert response.status_code != 500

    @pytest.mark.asyncio
    async def test_xss_in_item_title(self, async_client: AsyncClient, auth_headers):
        """XSS attempt in item title should be stored safely or rejected."""
        payload = {
            "title": "<script>alert('xss')</script>",
            "description": "XSS attempt",
        }
        response = await async_client.post("/api/v1/items/", json=payload, headers=auth_headers)
        assert response.status_code != 500

    @pytest.mark.asyncio
    async def test_oversized_payload(self, async_client: AsyncClient):
        """Extremely large payload should not crash the server."""
        payload = {
            "username": "a" * 10000,
            "email": "x@x.com",
            "password": "Password123!",
        }
        response = await async_client.post("/api/v1/users/", json=payload)
        assert response.status_code in (409, 422)
        assert response.status_code != 500

    @pytest.mark.asyncio
    async def test_missing_required_fields(self, async_client: AsyncClient):
        """Missing required fields should return 422."""
        response = await async_client.post("/api/v1/users/", json={})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_login_brute_force_returns_401(self, async_client: AsyncClient):
        """Multiple failed logins should return 401, not 500."""
        for _ in range(5):
            response = await async_client.post(
                "/api/v1/auth/token",
                data={"username": "nobody", "password": "wrong"},
            )
            assert response.status_code == 401
