from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from services.moderation_service.app.models import ModerationStatus


class QueueRequest(BaseModel):
    video_id: UUID
    author_id: UUID
    video_url: str


class ModerationItemResponse(BaseModel):
    id: UUID
    video_id: UUID
    author_id: UUID
    video_url: str
    status: ModerationStatus
    reason: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class RejectRequest(BaseModel):
    reason: str
