"""Additional integration tests for API endpoints."""

import uuid

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


class TestUserManagement:
    """Additional tests for user management endpoints."""

    @pytest.mark.asyncio
    async def test_register_with_duplicate_email(self, async_client: AsyncClient, test_user):
        """Register with existing email should return 409."""
        payload = {
            "username": "anotheruser",
            "email": test_user.email,
            "password": "Password123!",
        }
        response = await async_client.post("/api/v1/users/", json=payload)
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_register_with_short_password(self, async_client: AsyncClient):
        """Register with short password should return 422."""
        payload = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "short",
        }
        response = await async_client.post("/api/v1/users/", json=payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_other_user_as_regular_user_forbidden(
        self, async_client: AsyncClient, auth_headers, test_superuser
    ):
        """Regular user cannot get another user's profile."""
        response = await async_client.get(f"/api/v1/users/{test_superuser.id}", headers=auth_headers)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_nonexistent_user_returns_404(self, async_client: AsyncClient, auth_headers, superuser_headers):
        """Get nonexistent user should return 404."""
        fake_id = uuid.uuid4()
        # As superuser (can see any user)
        response = await async_client.get(f"/api/v1/users/{fake_id}", headers=superuser_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_other_user_forbidden(self, async_client: AsyncClient, auth_headers, test_superuser):
        """User cannot update another user's profile."""
        payload = {"full_name": "Hacked Name"}
        response = await async_client.patch(f"/api/v1/users/{test_superuser.id}", json=payload, headers=auth_headers)
        assert response.status_code == 403


class TestSuperUserEndpoints:
    """Tests for superuser-only endpoints."""

    @pytest.mark.asyncio
    async def test_list_users_as_regular_user_forbidden(self, async_client: AsyncClient, auth_headers):
        """Regular user cannot list all users."""
        response = await async_client.get("/api/v1/users/", headers=auth_headers)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_list_users_as_superuser(self, async_client: AsyncClient, superuser_headers):
        """Superuser can list all users."""
        response = await async_client.get("/api/v1/users/", headers=superuser_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_delete_user_as_superuser(self, async_client: AsyncClient, superuser_headers, test_user):
        """Superuser can deactivate a user."""
        response = await async_client.delete(f"/api/v1/users/{test_user.id}", headers=superuser_headers)
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_nonexistent_user_as_superuser(self, async_client: AsyncClient, superuser_headers):
        """Deleting nonexistent user returns 404."""
        fake_id = uuid.uuid4()
        response = await async_client.delete(f"/api/v1/users/{fake_id}", headers=superuser_headers)
        assert response.status_code == 404


class TestItemCRUD:
    """Additional tests for item CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_item_as_public(self, async_client: AsyncClient, auth_headers):
        """Create public item should work."""
        payload = {"title": "Public Item", "is_public": True}
        response = await async_client.post("/api/v1/items/", json=payload, headers=auth_headers)
        assert response.status_code == 201
        assert response.json()["is_public"] is True

    @pytest.mark.asyncio
    async def test_update_item_title(self, async_client: AsyncClient, auth_headers, test_item):
        """Update item title should work."""
        payload = {"title": "Updated Title"}
        response = await async_client.patch(f"/api/v1/items/{test_item.id}", json=payload, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"

    @pytest.mark.asyncio
    async def test_update_item_description(self, async_client: AsyncClient, auth_headers, test_item):
        """Update item description should work."""
        payload = {"description": "New description"}
        response = await async_client.patch(f"/api/v1/items/{test_item.id}", json=payload, headers=auth_headers)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_item_without_auth_forbidden(self, async_client: AsyncClient, test_item):
        """Get item without auth should return 401."""
        response = await async_client.get(f"/api/v1/items/{test_item.id}")
        assert response.status_code == 401


class TestTokenRefresh:
    """Tests for token refresh endpoint."""

    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self, async_client: AsyncClient):
        """Refresh with invalid token should return 401."""
        response = await async_client.post("/api/v1/auth/refresh", json={"refresh_token": "invalid.token.here"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_with_access_token_fails(self, async_client: AsyncClient, test_user):
        """Using access token for refresh should fail."""
        from src.app.core.security import create_access_token

        token = create_access_token(subject=str(test_user.id))

        response = await async_client.post("/api/v1/auth/refresh", json={"refresh_token": token})
        assert response.status_code == 401


class TestHealthComponents:
    """Additional tests for health endpoint."""

    @pytest.mark.asyncio
    async def test_health_database_component(self, async_client: AsyncClient):
        """Health response should include database component."""
        response = await async_client.get("/api/v1/health")
        data = response.json()
        assert "database" in data["components"]

    @pytest.mark.asyncio
    async def test_health_redis_component(self, async_client: AsyncClient):
        """Health response should include redis component."""
        response = await async_client.get("/api/v1/health")
        data = response.json()
        assert "redis" in data["components"]
