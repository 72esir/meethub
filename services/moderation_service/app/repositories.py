import httpx
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.moderation_service.app.models import ModerationQueueItem, ModerationStatus


class ModerationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_item(self, item: ModerationQueueItem) -> ModerationQueueItem:
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def get_pending_items(self) -> list[ModerationQueueItem]:
        return self.db.scalars(
            select(ModerationQueueItem)
            .where(ModerationQueueItem.status == ModerationStatus.pending)
            .order_by(ModerationQueueItem.created_at)
        ).all()

    def get_item(self, item_id: UUID) -> ModerationQueueItem | None:
        return self.db.get(ModerationQueueItem, item_id)

    def commit(self) -> None:
        self.db.commit()


class FeedStatusGateway:
    def __init__(self, base_url: str, internal_api_key: str) -> None:
        self.base_url = base_url
        self.internal_api_key = internal_api_key

    async def sync_status(self, video_id: UUID, status_value: str) -> None:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.put(
                f"{self.base_url}/internal/videos/{video_id}/status",
                headers={"X-Internal-Key": self.internal_api_key},
                json={"status": status_value},
            )
            response.raise_for_status()
