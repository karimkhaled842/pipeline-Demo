"""Unit tests for core security utilities."""

import pytest

from src.app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    """Tests for bcrypt password hashing."""

    def test_hash_password_returns_string(self):
        """hash_password should return a non-empty string."""
        result = hash_password("MySecurePass123!")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_hash_is_not_plaintext(self):
        """The hash must differ from the plain-text password."""
        plain = "MySecurePass123!"
        assert hash_password(plain) != plain

    def test_two_hashes_differ(self):
        """bcrypt uses a random salt — same input yields different hashes."""
        h1 = hash_password("SamePass!")
        h2 = hash_password("SamePass!")
        assert h1 != h2

    def test_verify_correct_password(self):
        """verify_password returns True for a matching password."""
        plain = "CorrectPassword!"
        hashed = hash_password(plain)
        assert verify_password(plain, hashed) is True

    def test_verify_wrong_password(self):
        """verify_password returns False for a wrong password."""
        hashed = hash_password("CorrectPassword!")
        assert verify_password("WrongPassword!", hashed) is False

    def test_verify_empty_password_fails(self):
        """Empty password should not verify against a real hash."""
        hashed = hash_password("SomePassword!")
        assert verify_password("", hashed) is False


class TestJWTTokens:
    """Tests for JWT token creation and decoding."""

    def test_create_access_token_returns_string(self):
        """create_access_token should return a JWT string."""
        token = create_access_token("user-123")
        assert isinstance(token, str)
        assert len(token.split(".")) == 3  # header.payload.signature

    def test_access_token_contains_correct_subject(self):
        """The decoded token should contain the correct 'sub' claim."""
        token = create_access_token("user-abc")
        claims = decode_token(token)
        assert claims["sub"] == "user-abc"

    def test_access_token_type_is_access(self):
        """Access tokens must have type='access'."""
        token = create_access_token("user-1")
        claims = decode_token(token)
        assert claims["type"] == "access"

    def test_refresh_token_type_is_refresh(self):
        """Refresh tokens must have type='refresh'."""
        token = create_refresh_token("user-1")
        claims = decode_token(token)
        assert claims["type"] == "refresh"

    def test_access_token_has_expiry(self):
        """Access tokens must carry an 'exp' claim."""
        token = create_access_token("user-1")
        claims = decode_token(token)
        assert "exp" in claims

    def test_access_token_extra_claims(self):
        """Extra claims should be embedded in the token."""
        token = create_access_token("user-1", extra_claims={"role": "admin"})
        claims = decode_token(token)
        assert claims["role"] == "admin"

    def test_decode_invalid_token_raises(self):
        """Decoding a malformed token should raise JWTError."""
        from jose import JWTError

        with pytest.raises(JWTError):
            decode_token("not.a.valid.token")

    def test_decode_tampered_token_raises(self):
        """Tampering with the signature should raise JWTError."""
        from jose import JWTError

        token = create_access_token("user-1")
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(JWTError):
            decode_token(tampered)
