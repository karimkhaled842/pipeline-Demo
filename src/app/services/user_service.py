"""User CRUD service layer."""

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.logging import get_logger
from src.app.core.security import hash_password, verify_password
from src.app.models.models import User
from src.app.schemas.schemas import UserCreate, UserUpdate
from src.app.services.cache import cache_delete, cache_get, cache_set

logger = get_logger(__name__)

_CACHE_PREFIX = "user"
_CACHE_TTL = 300


def _cache_key(user_id: uuid.UUID) -> str:
    return f"{_CACHE_PREFIX}:{user_id}"


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    """Fetch a user by primary-key, with a cache layer."""
    cached = await cache_get(_cache_key(user_id))
    if cached:
        return cached  # type: ignore[return-value]

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        await cache_set(_cache_key(user_id), _user_to_dict(user), _CACHE_TTL)
    return user


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    """Fetch a user by username."""
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Fetch a user by email address."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def list_users(db: AsyncSession, *, skip: int = 0, limit: int = 20) -> tuple[list[User], int]:
    """Return a paginated list of users with total count."""
    total_result = await db.execute(select(func.count()).select_from(User))
    total = total_result.scalar_one()

    result = await db.execute(select(User).offset(skip).limit(limit))
    users = list(result.scalars().all())
    return users, total


async def create_user(db: AsyncSession, payload: UserCreate) -> User:
    """Create and persist a new user."""
    user = User(
        username=payload.username,
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    logger.info("user_created", user_id=str(user.id), username=user.username)
    return user


async def update_user(db: AsyncSession, user: User, payload: UserUpdate) -> User:
    """Apply partial updates to an existing user."""
    update_data = payload.model_dump(exclude_none=True)
    if "password" in update_data:
        update_data["hashed_password"] = hash_password(update_data.pop("password"))

    for field, value in update_data.items():
        setattr(user, field, value)

    await db.flush()
    await db.refresh(user)
    await cache_delete(_cache_key(user.id))
    logger.info("user_updated", user_id=str(user.id))
    return user


async def delete_user(db: AsyncSession, user: User) -> None:
    """Soft-delete: deactivate the user."""
    user.is_active = False
    await db.flush()
    await cache_delete(_cache_key(user.id))
    logger.info("user_deactivated", user_id=str(user.id))


async def authenticate_user(db: AsyncSession, username: str, password: str) -> User | None:
    """Return the user if credentials are valid, else None."""
    user = await get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return user


def _user_to_dict(user: User) -> dict[str, Any]:
    """Serialise a User ORM object to a plain dict (for caching)."""
    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
    }
