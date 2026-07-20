"""User management endpoints."""

import uuid

from fastapi import APIRouter, HTTPException, status

from src.app.api.v1.deps import CurrentUser, DbSession, Pagination, SuperUser
from src.app.core.logging import get_logger
from src.app.schemas.schemas import (
    PaginatedResponse,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from src.app.services import user_service

logger = get_logger(__name__)
router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def create_user(payload: UserCreate, db: DbSession) -> UserResponse:
    """Register a new user account (public endpoint)."""
    if await user_service.get_user_by_username(db, payload.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already registered",
        )
    if await user_service.get_user_by_email(db, payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    user = await user_service.create_user(db, payload)
    return UserResponse.model_validate(user)


@router.get(
    "/",
    response_model=PaginatedResponse,
    summary="List all users (superuser only)",
)
async def list_users(_: SuperUser, db: DbSession, pagination: Pagination) -> PaginatedResponse:
    """Return a paginated list of all users (superuser only)."""
    users, total = await user_service.list_users(db, skip=pagination.skip, limit=pagination.limit)
    return PaginatedResponse(
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        items=[UserResponse.model_validate(u) for u in users],
    )


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get a user by ID",
)
async def get_user(
    user_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> UserResponse:
    """Return a user by ID. Non-superusers can only view their own profile."""
    if not current_user.is_superuser and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    user = await user_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse.model_validate(user)


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update a user",
)
async def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> UserResponse:
    """Update user fields. Non-superusers can only update their own profile."""
    if not current_user.is_superuser and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    user = await user_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    updated = await user_service.update_user(db, user, payload)
    return UserResponse.model_validate(updated)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate a user (superuser only)",
)
async def delete_user(user_id: uuid.UUID, _: SuperUser, db: DbSession) -> None:
    """Deactivate a user account (superuser only)."""
    user = await user_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await user_service.delete_user(db, user)
