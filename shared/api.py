from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from shared.security import decode_token

bearer_scheme = HTTPBearer(auto_error=True)


def require_jwt(secret: str) -> Callable[[HTTPAuthorizationCredentials], str]:
    def dependency(credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)]) -> str:
        try:
            payload = decode_token(credentials.credentials, secret)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
        subject = payload.get("sub")
        if not subject:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing subject")
        return subject

    return dependency


def require_internal_api_key(expected_key: str) -> Callable[[str | None], None]:
    def dependency(x_internal_key: Annotated[str | None, Header()] = None) -> None:
        if x_internal_key != expected_key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid internal key")

    return dependency


def require_admin_token(expected_token: str) -> Callable[[str | None], None]:
    def dependency(x_admin_token: Annotated[str | None, Header()] = None) -> None:
        if x_admin_token != expected_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid admin token")

    return dependency
