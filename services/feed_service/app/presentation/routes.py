from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from services.feed_service.app.application.exceptions import InvalidFollowError, VideoNotFoundError
from services.feed_service.app.application.services import FeedService
from services.feed_service.app.presentation.dependencies import get_current_user, get_feed_service, get_internal_auth
from services.feed_service.app.schemas import (
    FeedResponse,
    FollowActionResponse,
    FollowListItemResponse,
    FollowStatusResponse,
    InternalCreateVideoRequest,
    UpdateStatusRequest,
    VideoResponse,
)

router = APIRouter()


@router.get("/feed/foryou", response_model=FeedResponse)
def for_you(
    _: Annotated[str, Depends(get_current_user)],
    service: Annotated[FeedService, Depends(get_feed_service)],
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, le=50),
) -> FeedResponse:
    return service.for_you(cursor=cursor, limit=limit)


@router.get("/feed/following", response_model=FeedResponse)
def following_feed(
    user_id: Annotated[str, Depends(get_current_user)],
    service: Annotated[FeedService, Depends(get_feed_service)],
    cursor: int = Query(default=0, ge=0),
    limit: int = Query(default=20, le=50),
) -> FeedResponse:
    return service.following(user_id=user_id, cursor=cursor, limit=limit)


@router.get("/videos/{video_id}", response_model=VideoResponse)
def get_video(
    video_id: UUID,
    _: Annotated[str, Depends(get_current_user)],
    service: Annotated[FeedService, Depends(get_feed_service)],
):
    try:
        return service.get_video(video_id=video_id)
    except VideoNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/videos/{video_id}/like")
def toggle_like(
    video_id: UUID,
    user_id: Annotated[str, Depends(get_current_user)],
    service: Annotated[FeedService, Depends(get_feed_service)],
) -> dict[str, bool]:
    return service.toggle_like(video_id=video_id, user_id=user_id)


@router.post("/videos/{video_id}/view")
def record_view(
    video_id: UUID,
    user_id: Annotated[str, Depends(get_current_user)],
    service: Annotated[FeedService, Depends(get_feed_service)],
) -> dict[str, bool]:
    return service.record_view(video_id=video_id, user_id=user_id)


@router.post("/users/{target_user_id}/follow")
def follow_user(
    target_user_id: UUID,
    user_id: Annotated[str, Depends(get_current_user)],
    service: Annotated[FeedService, Depends(get_feed_service)],
) -> FollowActionResponse:
    try:
        return service.follow_user(target_user_id=target_user_id, user_id=user_id)
    except InvalidFollowError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/users/{target_user_id}/follow", response_model=FollowActionResponse)
def unfollow_user(
    target_user_id: UUID,
    user_id: Annotated[str, Depends(get_current_user)],
    service: Annotated[FeedService, Depends(get_feed_service)],
) -> FollowActionResponse:
    try:
        return service.unfollow_user(target_user_id=target_user_id, user_id=user_id)
    except InvalidFollowError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/users/{target_user_id}/follow-status", response_model=FollowStatusResponse)
def follow_status(
    target_user_id: UUID,
    user_id: Annotated[str, Depends(get_current_user)],
    service: Annotated[FeedService, Depends(get_feed_service)],
) -> FollowStatusResponse:
    return service.follow_status(target_user_id=target_user_id, user_id=user_id)


@router.get("/users/{target_user_id}/followers", response_model=list[FollowListItemResponse])
def followers(
    target_user_id: UUID,
    _: Annotated[str, Depends(get_current_user)],
    service: Annotated[FeedService, Depends(get_feed_service)],
) -> list[FollowListItemResponse]:
    return service.followers(target_user_id=target_user_id)


@router.get("/users/{target_user_id}/following", response_model=list[FollowListItemResponse])
def following_users(
    target_user_id: UUID,
    _: Annotated[str, Depends(get_current_user)],
    service: Annotated[FeedService, Depends(get_feed_service)],
) -> list[FollowListItemResponse]:
    return service.following_list(target_user_id=target_user_id)


@router.get("/users/{target_user_id}/videos", response_model=list[VideoResponse])
def user_videos(
    target_user_id: UUID,
    _: Annotated[str, Depends(get_current_user)],
    service: Annotated[FeedService, Depends(get_feed_service)],
):
    return service.user_videos(target_user_id=target_user_id)


@router.post("/internal/videos", response_model=VideoResponse, status_code=status.HTTP_201_CREATED)
def internal_create_video(
    payload: InternalCreateVideoRequest,
    service: Annotated[FeedService, Depends(get_feed_service)],
    _: Annotated[None, Depends(get_internal_auth)],
):
    return service.internal_create_video(payload)


@router.put("/internal/videos/{video_id}/status")
def internal_update_status(
    video_id: UUID,
    payload: UpdateStatusRequest,
    service: Annotated[FeedService, Depends(get_feed_service)],
    _: Annotated[None, Depends(get_internal_auth)],
) -> dict[str, str]:
    try:
        return service.internal_update_status(video_id=video_id, payload=payload)
    except VideoNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
