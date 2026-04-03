from uuid import UUID

from services.moderation_service.app.application.exceptions import ModerationItemNotFoundError
from services.moderation_service.app.models import ModerationQueueItem, ModerationStatus
from services.moderation_service.app.repositories import ModerationRepository


class ModerationService:
    def __init__(self, repository: ModerationRepository, feed_gateway) -> None:
        self.repository = repository
        self.feed_gateway = feed_gateway

    def queue_item(self, *, video_id: UUID, author_id: UUID, video_url: str) -> ModerationQueueItem:
        return self.repository.create_item(ModerationQueueItem(video_id=video_id, author_id=author_id, video_url=video_url))

    def pending_items(self) -> list[ModerationQueueItem]:
        return self.repository.get_pending_items()

    async def approve(self, item_id: UUID) -> dict[str, str]:
        item = self.repository.get_item(item_id)
        if not item:
            raise ModerationItemNotFoundError("moderation item not found")
        item.status = ModerationStatus.approved
        self.repository.commit()
        await self.feed_gateway.sync_status(item.video_id, ModerationStatus.approved.value)
        return {"status": item.status.value}

    async def reject(self, item_id: UUID, reason: str) -> dict[str, str]:
        item = self.repository.get_item(item_id)
        if not item:
            raise ModerationItemNotFoundError("moderation item not found")
        item.status = ModerationStatus.rejected
        item.reason = reason
        self.repository.commit()
        await self.feed_gateway.sync_status(item.video_id, ModerationStatus.rejected.value)
        return {"status": item.status.value}
