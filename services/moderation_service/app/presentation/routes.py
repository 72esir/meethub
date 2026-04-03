from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from services.moderation_service.app.application.exceptions import ModerationItemNotFoundError
from services.moderation_service.app.application.services import ModerationService
from services.moderation_service.app.presentation.dependencies import get_admin_auth, get_internal_auth, get_moderation_service
from services.moderation_service.app.schemas import ModerationItemResponse, QueueRequest, RejectRequest

router = APIRouter()


@router.post("/moderation/queue", response_model=ModerationItemResponse, status_code=status.HTTP_201_CREATED)
def queue_item(
    payload: QueueRequest,
    service: Annotated[ModerationService, Depends(get_moderation_service)],
    _: Annotated[None, Depends(get_internal_auth)],
):
    return service.queue_item(video_id=payload.video_id, author_id=payload.author_id, video_url=payload.video_url)


@router.get("/moderation/pending", response_model=list[ModerationItemResponse])
def pending_items(
    service: Annotated[ModerationService, Depends(get_moderation_service)],
    _: Annotated[None, Depends(get_admin_auth)],
):
    return service.pending_items()


@router.post("/moderation/{item_id}/approve")
async def approve(
    item_id: UUID,
    service: Annotated[ModerationService, Depends(get_moderation_service)],
    _: Annotated[None, Depends(get_admin_auth)],
) -> dict[str, str]:
    try:
        return await service.approve(item_id)
    except ModerationItemNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/moderation/{item_id}/reject")
async def reject(
    item_id: UUID,
    payload: RejectRequest,
    service: Annotated[ModerationService, Depends(get_moderation_service)],
    _: Annotated[None, Depends(get_admin_auth)],
) -> dict[str, str]:
    try:
        return await service.reject(item_id, payload.reason)
    except ModerationItemNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
