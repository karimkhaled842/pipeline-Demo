"""Shared FastAPI dependencies (auth, pagination, DB session)."""

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.logging import get_logger
from src.app.core.security import decode_token
from src.app.db.session import get_db
from src.app.models.models import User
from src.app.schemas.schemas import TokenData
from src.app.services import user_service

logger = get_logger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

# ── Auth dependencies ─────────────────────────────────────────────────────────


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Validate JWT and return the authenticated user."""
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        sub = payload.get("sub")
        token_type = payload.get("type")
        if sub is None or token_type != "access":
            raise credentials_exc
        token_data = TokenData(sub=sub, type=token_type)
    except JWTError as e:
        raise credentials_exc from e

    user = await user_service.get_user_by_id(db, uuid.UUID(token_data.sub))
    if user is None:
        raise credentials_exc
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Raise 403 if the authenticated user is inactive."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user


async def get_current_superuser(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """Raise 403 if the authenticated user is not a superuser."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return current_user


# ── Pagination ────────────────────────────────────────────────────────────────


class PaginationParams:
    """Common query-string pagination parameters."""

    def __init__(
        self,
        page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
        page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    ) -> None:
        self.page = page
        self.page_size = page_size

    @property
    def skip(self) -> int:
        """Offset for the database query."""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """Limit alias."""
        return self.page_size


# Type aliases for cleaner route signatures
CurrentUser = Annotated[User, Depends(get_current_active_user)]
SuperUser = Annotated[User, Depends(get_current_superuser)]
DbSession = Annotated[AsyncSession, Depends(get_db)]
Pagination = Annotated[PaginationParams, Depends()]
