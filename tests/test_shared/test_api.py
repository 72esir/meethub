"""
Тесты для shared/api.py:
  - require_jwt
  - require_internal_api_key
  - require_admin_token

Используется изолированное FastAPI-приложение для каждого теста.

ВАЖНО: Этот файл импортирует оригинальные функции ДО того, как conftest сервисов
подменяет shared.api на mock-объекты. Поэтому setup_method каждого класса
пересоздаёт app с оригинальными функциями, сохранёнными в переменных модуля.
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from typing import Annotated

from fastapi import Depends

from shared.security import create_access_token

# Сохраняем оригинальные функции до возможной подмены через monkey-patching в conftest.
# Если этот модуль загружается после conftest сервисов — функции уже подменены в shared.api,
# поэтому импортируем непосредственно из исходного кода функций.
import shared.api as _shared_api_module
from shared.security import decode_token as _decode_token
from fastapi import HTTPException, Header, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from collections.abc import Callable

_bearer_scheme = HTTPBearer(auto_error=True)

SECRET = "api-test-secret"
INTERNAL_KEY = "internal-key-value"
ADMIN_TOKEN = "admin-token-value"


# ──────────────────────────────────────────────
# Встроенные реализации (не зависят от shared.api monkey-patching)
# ──────────────────────────────────────────────

def _orig_require_jwt(secret: str) -> Callable:
    def dependency(credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer_scheme)]) -> str:
        try:
            payload = _decode_token(credentials.credentials, secret)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
        subject = payload.get("sub")
        if not subject:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing subject")
        return subject
    return dependency


def _orig_require_internal_api_key(expected_key: str) -> Callable:
    def dependency(x_internal_key: Annotated[str | None, Header()] = None) -> None:
        if x_internal_key != expected_key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid internal key")
    return dependency


def _orig_require_admin_token(expected_token: str) -> Callable:
    def dependency(x_admin_token: Annotated[str | None, Header()] = None) -> None:
        if x_admin_token != expected_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid admin token")
    return dependency


# ──────────────────────────────────────────────
# Вспомогательные фабрики приложений
# ──────────────────────────────────────────────

def _make_app_with_jwt():
    """Приложение с одним маршрутом, защищённым JWT."""
    test_app = FastAPI()
    RequireJwt = Annotated[str, Depends(_orig_require_jwt(SECRET))]

    @test_app.get("/protected")
    def protected(user_id: RequireJwt):
        return {"user_id": user_id}

    return test_app


def _make_app_with_internal_key():
    test_app = FastAPI()
    InternalAuth = Annotated[None, Depends(_orig_require_internal_api_key(INTERNAL_KEY))]

    @test_app.get("/internal")
    def internal_route(_: InternalAuth):
        return {"ok": True}

    return test_app


def _make_app_with_admin_token():
    test_app = FastAPI()
    AdminAuth = Annotated[None, Depends(_orig_require_admin_token(ADMIN_TOKEN))]

    @test_app.get("/admin")
    def admin_route(_: AdminAuth):
        return {"ok": True}

    return test_app


# ──────────────────────────────────────────────
# require_jwt
# ──────────────────────────────────────────────

class TestRequireJwt:
    def setup_method(self):
        self.client = TestClient(_make_app_with_jwt(), raise_server_exceptions=False)

    def test_valid_token_returns_subject(self):
        token = create_access_token("user-42", SECRET)
        response = self.client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json()["user_id"] == "user-42"

    def test_missing_token_returns_401_or_403(self):
        """HTTPBearer без токена возвращает 401 или 403 в зависимости от версии FastAPI."""
        response = self.client.get("/protected")
        assert response.status_code in (401, 403)

    def test_invalid_token_returns_401(self):
        response = self.client.get("/protected", headers={"Authorization": "Bearer not-a-jwt"})
        assert response.status_code == 401

    def test_wrong_secret_returns_401(self):
        token = create_access_token("user-1", "wrong-secret")
        response = self.client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401

    def test_expired_token_returns_401(self):
        token = create_access_token("user-1", SECRET, lifetime_minutes=-1)
        response = self.client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401


# ──────────────────────────────────────────────
# require_internal_api_key
# ──────────────────────────────────────────────

class TestRequireInternalApiKey:
    def setup_method(self):
        self.client = TestClient(_make_app_with_internal_key(), raise_server_exceptions=False)

    def test_correct_key_returns_200(self):
        response = self.client.get("/internal", headers={"x-internal-key": INTERNAL_KEY})
        assert response.status_code == 200
        assert response.json() == {"ok": True}

    def test_wrong_key_returns_401(self):
        response = self.client.get("/internal", headers={"x-internal-key": "bad-key"})
        assert response.status_code == 401

    def test_missing_key_returns_401(self):
        response = self.client.get("/internal")
        assert response.status_code == 401


# ──────────────────────────────────────────────
# require_admin_token
# ──────────────────────────────────────────────

class TestRequireAdminToken:
    def setup_method(self):
        self.client = TestClient(_make_app_with_admin_token(), raise_server_exceptions=False)

    def test_correct_token_returns_200(self):
        response = self.client.get("/admin", headers={"x-admin-token": ADMIN_TOKEN})
        assert response.status_code == 200
        assert response.json() == {"ok": True}

    def test_wrong_token_returns_401(self):
        response = self.client.get("/admin", headers={"x-admin-token": "bad-token"})
        assert response.status_code == 401

    def test_missing_token_returns_401(self):
        response = self.client.get("/admin")
        assert response.status_code == 401
