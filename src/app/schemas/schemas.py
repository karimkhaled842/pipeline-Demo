"""Pydantic request / response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# ── Token ─────────────────────────────────────────────────────────────────────


class Token(BaseModel):
    """JWT token pair returned after successful authentication."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Claims extracted from a decoded JWT."""

    sub: str
    type: str


# ── User ──────────────────────────────────────────────────────────────────────


class UserBase(BaseModel):
    """Shared user fields."""

    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: str | None = Field(default=None, max_length=255)


class UserCreate(UserBase):
    """Schema for creating a new user."""

    password: str = Field(..., min_length=8, max_length=128)


class UserUpdate(BaseModel):
    """Schema for updating an existing user (all fields optional)."""

    email: EmailStr | None = None
    full_name: str | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)
    is_active: bool | None = None


class UserResponse(UserBase):
    """Schema returned to clients (no password)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime


# ── Item ──────────────────────────────────────────────────────────────────────


class ItemBase(BaseModel):
    """Shared item fields."""

    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    is_public: bool = False


class ItemCreate(ItemBase):
    """Schema for creating a new item."""


class ItemUpdate(BaseModel):
    """Schema for updating an item (all fields optional)."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    is_public: bool | None = None


class ItemResponse(ItemBase):
    """Schema returned to clients."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# ── Health ────────────────────────────────────────────────────────────────────


class ComponentHealth(BaseModel):
    """Health status of a single dependency."""

    status: str
    latency_ms: float | None = None
    detail: str | None = None


class HealthResponse(BaseModel):
    """Overall application health response."""

    status: str
    version: str
    environment: str
    components: dict[str, ComponentHealth]


# ── Pagination ────────────────────────────────────────────────────────────────


class PaginatedResponse(BaseModel):
    """Generic paginated list wrapper."""

    total: int
    page: int
    page_size: int
    items: list


# ── Error ─────────────────────────────────────────────────────────────────────


class ErrorDetail(BaseModel):
    """Standardised error response body."""

    code: str
    message: str
    details: dict | None = None
