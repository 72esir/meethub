import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.db import Base


class ModerationStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class ModerationQueueItem(Base):
    __tablename__ = "moderation_queue"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    author_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    video_url: Mapped[str] = mapped_column(String(500))
    status: Mapped[ModerationStatus] = mapped_column(Enum(ModerationStatus), default=ModerationStatus.pending, index=True)
    moderator_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
