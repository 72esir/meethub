from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from services.moderation_service.app.application.services import ModerationService
from services.moderation_service.app.container import ModerationContainer
from shared.api import require_admin_token, require_internal_api_key


def get_container(request: Request) -> ModerationContainer:
    return request.app.state.container


def get_db(container: Annotated[ModerationContainer, Depends(get_container)]):
    yield from container.get_db()


def get_moderation_service(
    db: Annotated[Session, Depends(get_db)],
    container: Annotated[ModerationContainer, Depends(get_container)],
) -> ModerationService:
    return container.moderation_service(db)


def get_internal_auth(
    request: Request,
    container: Annotated[ModerationContainer, Depends(get_container)],
) -> None:
    return require_internal_api_key(container.settings.internal_api_key)(request.headers.get("x-internal-key"))


def get_admin_auth(
    request: Request,
    container: Annotated[ModerationContainer, Depends(get_container)],
) -> None:
    return require_admin_token(container.settings.admin_token)(request.headers.get("x-admin-token"))
