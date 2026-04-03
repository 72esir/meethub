from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from services.auth_service.app.application.services import AuthService
from services.auth_service.app.container import AuthContainer
from shared.api import require_jwt

bearer_scheme = HTTPBearer(auto_error=True)


def get_container(request: Request) -> AuthContainer:
    return request.app.state.container


def get_db(container: Annotated[AuthContainer, Depends(get_container)]):
    yield from container.get_db()


def get_auth_service(
    db: Annotated[Session, Depends(get_db)],
    container: Annotated[AuthContainer, Depends(get_container)],
) -> AuthService:
    return container.auth_service(db)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    container: Annotated[AuthContainer, Depends(get_container)],
) -> str:
    return require_jwt(container.settings.jwt_secret)(credentials)
