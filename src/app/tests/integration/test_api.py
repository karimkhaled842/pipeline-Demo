"""Integration tests for API endpoints."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


class TestHealthEndpoints:
    """Integration tests for /api/v1/health."""

    @pytest.mark.asyncio
    async def test_health_returns_200(self, async_client: AsyncClient):
        """GET /api/v1/health should return 200."""
        response = await async_client.get("/api/v1/health")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_health_response_structure(self, async_client: AsyncClient):
        """Health response must include status, version, environment, components."""
        response = await async_client.get("/api/v1/health")
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "environment" in data
        assert "components" in data

    @pytest.mark.asyncio
    async def test_liveness_probe(self, async_client: AsyncClient):
        """GET /api/v1/health/live should return alive."""
        response = await async_client.get("/api/v1/health/live")
        assert response.status_code == 200
        assert response.json()["status"] == "alive"

    @pytest.mark.asyncio
    async def test_readiness_probe(self, async_client: AsyncClient):
        """GET /api/v1/health/ready should return 200 when DB is up."""
        response = await async_client.get("/api/v1/health/ready")
        assert response.status_code in (200, 503)  # 503 if Redis is absent in CI


class TestUserRegistration:
    """Integration tests for user registration."""

    @pytest.mark.asyncio
    async def test_register_user_returns_201(self, async_client: AsyncClient):
        """POST /api/v1/users/ should create a user and return 201."""
        payload = {
            "username": "newuser1",
            "email": "newuser1@example.com",
            "password": "NewPassword123!",
        }
        response = await async_client.post("/api/v1/users/", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser1"
        assert "hashed_password" not in data

    @pytest.mark.asyncio
    async def test_register_duplicate_username_returns_409(self, async_client: AsyncClient, test_user):
        """Registering with an existing username should return 409."""
        payload = {
            "username": test_user.username,
            "email": "other@example.com",
            "password": "AnotherPass123!",
        }
        response = await async_client.post("/api/v1/users/", json=payload)
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_register_invalid_email_returns_422(self, async_client: AsyncClient):
        """Invalid email should return 422 Unprocessable Entity."""
        payload = {
            "username": "validuser",
            "email": "not-an-email",
            "password": "Password123!",
        }
        response = await async_client.post("/api/v1/users/", json=payload)
        assert response.status_code == 422


class TestAuthentication:
    """Integration tests for JWT authentication."""

    @pytest.mark.asyncio
    async def test_login_returns_tokens(self, async_client: AsyncClient, test_user):
        """Successful login should return access and refresh tokens."""
        response = await async_client.post(
            "/api/v1/auth/token",
            data={"username": test_user.username, "password": "TestPassword123!"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password_returns_401(self, async_client: AsyncClient, test_user):
        """Wrong password should return 401."""
        response = await async_client.post(
            "/api/v1/auth/token",
            data={"username": test_user.username, "password": "WrongPass!"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_me_requires_auth(self, async_client: AsyncClient):
        """GET /api/v1/auth/me without token should return 401."""
        response = await async_client.get("/api/v1/auth/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_me_returns_current_user(self, async_client: AsyncClient, auth_headers, test_user):
        """GET /api/v1/auth/me should return the authenticated user's profile."""
        response = await async_client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == test_user.username
        assert data["email"] == test_user.email


class TestItemEndpoints:
    """Integration tests for item CRUD."""

    @pytest.mark.asyncio
    async def test_create_item(self, async_client: AsyncClient, auth_headers):
        """POST /api/v1/items/ should create an item."""
        payload = {"title": "My Test Item", "description": "Some description", "is_public": False}
        response = await async_client.post("/api/v1/items/", json=payload, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "My Test Item"

    @pytest.mark.asyncio
    async def test_list_items_requires_auth(self, async_client: AsyncClient):
        """GET /api/v1/items/ without auth should return 401."""
        response = await async_client.get("/api/v1/items/")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_items_returns_paginated(self, async_client: AsyncClient, auth_headers, test_item):
        """GET /api/v1/items/ should return paginated structure."""
        response = await async_client.get("/api/v1/items/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data
        assert "page" in data

    @pytest.mark.asyncio
    async def test_get_item_by_id(self, async_client: AsyncClient, auth_headers, test_item):
        """GET /api/v1/items/{id} should return the item."""
        response = await async_client.get(f"/api/v1/items/{test_item.id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["id"] == test_item.id

    @pytest.mark.asyncio
    async def test_delete_item(self, async_client: AsyncClient, auth_headers, test_item):
        """DELETE /api/v1/items/{id} should return 204."""
        response = await async_client.delete(f"/api/v1/items/{test_item.id}", headers=auth_headers)
        assert response.status_code == 204
