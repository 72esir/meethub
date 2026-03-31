from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from services.upload_service.app.models import UploadStatus


class UploadRequest(BaseModel):
    file_name: str
    content_type: str = "video/mp4"


class UploadSessionResponse(BaseModel):
    upload_id: UUID
    upload_url: str
    s3_key: str
    expires_in_seconds: int = 1800


class CompleteUploadRequest(BaseModel):
    upload_id: UUID
    description: str = Field(default="", max_length=5000)
    hashtags: list[str] = Field(default_factory=list)


class UploadStatusResponse(BaseModel):
    id: UUID
    status: UploadStatus
    description: str | None
    hashtags: list[str]
    created_at: datetime
