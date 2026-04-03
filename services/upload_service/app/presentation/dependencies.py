from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from services.upload_service.app.application.services import UploadService
from services.upload_service.app.container import UploadContainer
from shared.api import require_jwt

bearer_scheme = HTTPBearer(auto_error=True)


def get_container(request: Request) -> UploadContainer:
    return request.app.state.container


def get_db(container: Annotated[UploadContainer, Depends(get_container)]):
    yield from container.get_db()


def get_upload_service(
    db: Annotated[Session, Depends(get_db)],
    container: Annotated[UploadContainer, Depends(get_container)],
) -> UploadService:
    return container.upload_service(db)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    container: Annotated[UploadContainer, Depends(get_container)],
) -> str:
    return require_jwt(container.settings.jwt_secret)(credentials)
