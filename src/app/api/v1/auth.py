"""Authentication endpoints — login, refresh, logout."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from src.app.api.v1.deps import CurrentUser, DbSession
from src.app.core.logging import get_logger
from src.app.core.security import create_access_token, create_refresh_token, decode_token
from src.app.schemas.schemas import Token, UserResponse
from src.app.services import user_service

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/token",
    response_model=Token,
    summary="Obtain JWT access + refresh tokens",
)
async def login(
    db: DbSession,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    """Authenticate with username/password and receive JWT tokens."""
    user = await user_service.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        logger.warning("login_failed", username=form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))
    logger.info("login_success", user_id=str(user.id))
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post(
    "/refresh",
    response_model=Token,
    summary="Refresh access token using a refresh token",
)
async def refresh_token(payload: dict) -> Token:
    """Exchange a valid refresh token for a new access + refresh token pair."""
    token = payload.get("refresh_token", "")
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        claims = decode_token(token)
        if claims.get("type") != "refresh":
            raise credentials_exc
        sub = claims["sub"]
    except Exception as e:
        raise credentials_exc from e

    access_token = create_access_token(subject=sub)
    new_refresh = create_refresh_token(subject=sub)
    return Token(access_token=access_token, refresh_token=new_refresh)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user",
)
async def get_me(current_user: CurrentUser) -> UserResponse:
    """Return the profile of the currently authenticated user."""
    return UserResponse.model_validate(current_user)
