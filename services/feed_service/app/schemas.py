from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from services.feed_service.app.models import VideoStatus


class LocationPayload(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=128)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class VideoResponse(BaseModel):
    id: UUID
    author_id: UUID
    description: str
    hashtags: list[str]
    location: LocationPayload | None = None
    hls_url: str
    thumbnail_url: str | None
    duration: int | None
    status: VideoStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class FeedResponse(BaseModel):
    items: list[VideoResponse]
    next_cursor: str | None


class InternalCreateVideoRequest(BaseModel):
    id: UUID
    author_id: UUID
    description: str = ""
    hashtags: list[str] = Field(default_factory=list)
    location: LocationPayload | None = None
    hls_url: str
    thumbnail_url: str | None = None
    duration: int | None = None


class UpdateStatusRequest(BaseModel):
    status: VideoStatus


class FollowActionResponse(BaseModel):
    following: bool


class FollowStatusResponse(BaseModel):
    user_id: UUID
    target_user_id: UUID
    is_following: bool
    followers_count: int
    following_count: int


class FollowListItemResponse(BaseModel):
    user_id: UUID
    created_at: datetime
