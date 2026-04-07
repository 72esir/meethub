from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from services.upload_service.app.models import UploadStatus


class UploadRequest(BaseModel):
    file_name: str
    content_type: str = "video/mp4"


class LocationPayload(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=128)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class UploadSessionResponse(BaseModel):
    upload_id: UUID
    upload_url: str
    s3_key: str
    expires_in_seconds: int = 1800


class CompleteUploadRequest(BaseModel):
    upload_id: UUID
    description: str = Field(default="", max_length=5000)
    hashtags: list[str] = Field(default_factory=list)
    location: LocationPayload | None = None


class UploadStatusResponse(BaseModel):
    id: UUID
    status: UploadStatus
    description: str | None
    location: LocationPayload | None
    error_message: str | None
    hashtags: list[str]
    created_at: datetime


class InternalUpdateUploadStatusRequest(BaseModel):
    status: UploadStatus
    error_message: str | None = None
