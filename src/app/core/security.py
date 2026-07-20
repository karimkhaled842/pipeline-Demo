"""JWT-based authentication and password hashing utilities."""

from datetime import UTC, datetime, timedelta
from typing import Any

from jose import jwt
from passlib.context import CryptContext

from src.app.core.config import get_settings
from src.app.core.logging import get_logger

logger = get_logger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Return bcrypt hash of the given plain-text password."""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if the password matches the stored hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str | int, extra_claims: dict[str, Any] | None = None) -> str:
    """Create a signed JWT access token."""
    settings = get_settings()
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(UTC),
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str | int) -> str:
    """Create a signed JWT refresh token."""
    settings = get_settings()
    expire = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(UTC),
        "type": "refresh",
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT; raise JWTError on failure."""
    settings = get_settings()
    return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
