"""
Тесты для shared/security.py:
  - hash_password / verify_password
  - create_access_token / decode_token
  - create_refresh_token
"""
import time

import pytest

from shared.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

SECRET = "test-secret-key"


# ──────────────────────────────────────────────
# hash_password / verify_password
# ──────────────────────────────────────────────

class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        hashed = hash_password("my_password")
        assert hashed != "my_password"

    def test_verify_correct_password(self):
        hashed = hash_password("secure123")
        assert verify_password("secure123", hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("correct_pass")
        assert verify_password("wrong_pass", hashed) is False

    def test_two_hashes_differ(self):
        """Bcrypt использует соль — одинаковый пароль даёт разные хэши."""
        h1 = hash_password("same_password")
        h2 = hash_password("same_password")
        assert h1 != h2


# ──────────────────────────────────────────────
# create_access_token / decode_token
# ──────────────────────────────────────────────

class TestJwt:
    def test_token_contains_subject(self):
        token = create_access_token("user-123", SECRET)
        payload = decode_token(token, SECRET)
        assert payload["sub"] == "user-123"

    def test_token_contains_iat_and_exp(self):
        token = create_access_token("user-456", SECRET, lifetime_minutes=30)
        payload = decode_token(token, SECRET)
        assert "iat" in payload
        assert "exp" in payload
        assert payload["exp"] > payload["iat"]

    def test_lifetime_respected(self):
        token = create_access_token("u", SECRET, lifetime_minutes=10)
        payload = decode_token(token, SECRET)
        # exp должен быть ~через 10 минут от сейчас
        remaining = payload["exp"] - time.time()
        assert 9 * 60 < remaining < 11 * 60

    def test_invalid_token_raises_value_error(self):
        with pytest.raises(ValueError, match="invalid token"):
            decode_token("not.a.valid.token", SECRET)

    def test_wrong_secret_raises_value_error(self):
        token = create_access_token("user-789", SECRET)
        with pytest.raises(ValueError, match="invalid token"):
            decode_token(token, "wrong-secret")

    def test_expired_token_raises_value_error(self):
        """Токен с истёкшим сроком действия должен вызвать ValueError."""
        token = create_access_token("u", SECRET, lifetime_minutes=-1)
        with pytest.raises(ValueError, match="invalid token"):
            decode_token(token, SECRET)


# ──────────────────────────────────────────────
# create_refresh_token
# ──────────────────────────────────────────────

class TestRefreshToken:
    def test_token_is_string(self):
        token = create_refresh_token()
        assert isinstance(token, str)

    def test_token_length(self):
        """Два uuid4().hex = 32+32 = 64 символа."""
        token = create_refresh_token()
        assert len(token) == 64

    def test_tokens_are_unique(self):
        t1 = create_refresh_token()
        t2 = create_refresh_token()
        assert t1 != t2
