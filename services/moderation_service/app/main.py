from typing import Annotated
from uuid import UUID

import httpx
from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from services.moderation_service.app.models import ModerationQueueItem, ModerationStatus
from services.moderation_service.app.schemas import ModerationItemResponse, QueueRequest, RejectRequest
from services.moderation_service.app.settings import settings
from shared.api import require_admin_token, require_internal_api_key
from shared.db import Base, build_session_factory, get_db
from shared.startup import wait_for_database

app = FastAPI(title="Moderation Service")
session_factory = build_session_factory(settings.database_url)
engine = session_factory.kw["bind"]


def db_dependency():
    yield from get_db(session_factory)


DbSession = Annotated[Session, Depends(db_dependency)]
InternalAuth = Annotated[None, Depends(require_internal_api_key(settings.internal_api_key))]
AdminAuth = Annotated[None, Depends(require_admin_token(settings.admin_token))]


@app.on_event("startup")
def startup() -> None:
    wait_for_database(engine, "moderation-service")
    Base.metadata.create_all(bind=engine)


async def sync_feed_status(video_id: UUID, status_value: str) -> None:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.put(
            f"{settings.feed_service_url}/internal/videos/{video_id}/status",
            headers={"X-Internal-Key": settings.internal_api_key},
            json={"status": status_value},
        )
        response.raise_for_status()


@app.post("/moderation/queue", response_model=ModerationItemResponse, status_code=status.HTTP_201_CREATED)
def queue_item(payload: QueueRequest, db: DbSession, _: InternalAuth) -> ModerationQueueItem:
    item = ModerationQueueItem(video_id=payload.video_id, author_id=payload.author_id, video_url=payload.video_url)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@app.get("/moderation/pending", response_model=list[ModerationItemResponse])
def pending_items(db: DbSession, _: AdminAuth) -> list[ModerationQueueItem]:
    return db.scalars(
        select(ModerationQueueItem).where(ModerationQueueItem.status == ModerationStatus.pending).order_by(ModerationQueueItem.created_at)
    ).all()


@app.post("/moderation/{item_id}/approve")
async def approve(item_id: UUID, db: DbSession, _: AdminAuth) -> dict[str, str]:
    item = db.get(ModerationQueueItem, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="moderation item not found")
    item.status = ModerationStatus.approved
    db.commit()
    await sync_feed_status(item.video_id, ModerationStatus.approved.value)
    return {"status": item.status.value}


@app.post("/moderation/{item_id}/reject")
async def reject(item_id: UUID, payload: RejectRequest, db: DbSession, _: AdminAuth) -> dict[str, str]:
    item = db.get(ModerationQueueItem, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="moderation item not found")
    item.status = ModerationStatus.rejected
    item.reason = payload.reason
    db.commit()
    await sync_feed_status(item.video_id, ModerationStatus.rejected.value)
    return {"status": item.status.value}
