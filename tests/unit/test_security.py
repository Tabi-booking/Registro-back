from __future__ import annotations

import time

import pytest
from jose import JWTError

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    hash_password,
    hash_token,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_differs_from_plain(self):
        hashed = hash_password("MyPassword123")
        assert hashed != "MyPassword123"

    def test_verify_correct_password(self):
        hashed = hash_password("MyPassword123")
        assert verify_password("MyPassword123", hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("MyPassword123")
        assert verify_password("WrongPassword", hashed) is False

    def test_hash_is_unique_per_call(self):
        pw = "MyPassword123"
        h1 = hash_password(pw)
        h2 = hash_password(pw)
        assert h1 != h2  # bcrypt uses random salt


class TestJWT:
    def test_create_and_decode_token(self):
        token = create_access_token(subject=42)
        payload = decode_access_token(token)
        assert payload["sub"] == "42"
        assert payload["type"] == "access"

    def test_extra_claims(self):
        token = create_access_token(subject=1, extra_claims={"role": "admin"})
        payload = decode_access_token(token)
        assert payload["role"] == "admin"

    def test_invalid_token_raises(self):
        with pytest.raises(JWTError):
            decode_access_token("this.is.invalid")

    def test_tampered_token_raises(self):
        token = create_access_token(subject=1)
        # Flip last char
        tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
        with pytest.raises(JWTError):
            decode_access_token(tampered)


class TestRefreshToken:
    def test_returns_tuple(self):
        raw, hashed = create_refresh_token()
        assert isinstance(raw, str)
        assert isinstance(hashed, str)
        assert raw != hashed

    def test_hash_is_deterministic(self):
        raw, _ = create_refresh_token()
        h1 = hash_token(raw)
        h2 = hash_token(raw)
        assert h1 == h2

    def test_different_tokens_different_hashes(self):
        raw1, _ = create_refresh_token()
        raw2, _ = create_refresh_token()
        assert raw1 != raw2
        assert hash_token(raw1) != hash_token(raw2)
