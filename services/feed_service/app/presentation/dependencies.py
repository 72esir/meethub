from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from services.feed_service.app.application.services import FeedService
from services.feed_service.app.container import FeedContainer
from shared.api import require_internal_api_key, require_jwt

bearer_scheme = HTTPBearer(auto_error=True)


def get_container(request: Request) -> FeedContainer:
    return request.app.state.container


def get_db(container: Annotated[FeedContainer, Depends(get_container)]):
    yield from container.get_db()


def get_feed_service(
    db: Annotated[Session, Depends(get_db)],
    container: Annotated[FeedContainer, Depends(get_container)],
) -> FeedService:
    return container.feed_service(db)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    container: Annotated[FeedContainer, Depends(get_container)],
) -> str:
    return require_jwt(container.settings.jwt_secret)(credentials)


def get_internal_auth(
    request: Request,
    container: Annotated[FeedContainer, Depends(get_container)],
) -> None:
    return require_internal_api_key(container.settings.internal_api_key)(request.headers.get("x-internal-key"))
