from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from services.feed_service.app.models import VideoStatus


class VideoResponse(BaseModel):
    id: UUID
    author_id: UUID
    description: str
    hashtags: list[str]
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
    hls_url: str
    thumbnail_url: str | None = None
    duration: int | None = None


class UpdateStatusRequest(BaseModel):
    status: VideoStatus
