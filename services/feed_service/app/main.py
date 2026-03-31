from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query, status
from redis import Redis
from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from services.feed_service.app.models import Follow, Like, Video, VideoStatus, View
from services.feed_service.app.schemas import FeedResponse, InternalCreateVideoRequest, UpdateStatusRequest, VideoResponse
from services.feed_service.app.settings import settings
from shared.api import require_internal_api_key, require_jwt
from shared.db import Base, build_session_factory, get_db

app = FastAPI(title="Feed Service")
session_factory = build_session_factory(settings.database_url)
engine = session_factory.kw["bind"]
cache = Redis.from_url(settings.redis_cache_url, decode_responses=True)


def db_dependency():
    yield from get_db(session_factory)


DbSession = Annotated[Session, Depends(db_dependency)]
CurrentUser = Annotated[str, Depends(require_jwt(settings.jwt_secret))]
InternalAuth = Annotated[None, Depends(require_internal_api_key(settings.internal_api_key))]


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)


def serialize(video: Video) -> VideoResponse:
    return VideoResponse.model_validate(video)


def fetch_videos_by_ids(db: Session, ids: list[str]) -> list[Video]:
    if not ids:
        return []
    videos = db.scalars(select(Video).where(Video.id.in_([UUID(item) for item in ids]), Video.status == VideoStatus.approved)).all()
    order = {video_id: idx for idx, video_id in enumerate(ids)}
    return sorted(videos, key=lambda item: order.get(str(item.id), 0))


@app.get("/feed/foryou", response_model=FeedResponse)
def for_you(
    _: CurrentUser,
    db: DbSession,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, le=50),
) -> FeedResponse:
    cache_key = "feed:foryou"
    cached_ids = cache.lrange(cache_key, 0, limit - 1)
    if cached_ids:
        items = [serialize(video) for video in fetch_videos_by_ids(db, cached_ids)]
        return FeedResponse(items=items, next_cursor=items[-1].created_at.isoformat() if items else None)

    stmt = select(Video).where(Video.status == VideoStatus.approved)
    if cursor:
        stmt = stmt.where(Video.created_at < datetime.fromisoformat(cursor))
    videos = db.scalars(stmt.order_by(desc(Video.created_at)).limit(limit)).all()
    if videos:
        cache.delete(cache_key)
        for video in videos:
            cache.rpush(cache_key, str(video.id))
        cache.expire(cache_key, 30)
    return FeedResponse(items=[serialize(video) for video in videos], next_cursor=videos[-1].created_at.isoformat() if videos else None)


@app.get("/feed/following", response_model=FeedResponse)
def following_feed(
    user_id: CurrentUser,
    db: DbSession,
    cursor: int = Query(default=0, ge=0),
    limit: int = Query(default=20, le=50),
) -> FeedResponse:
    cache_key = f"feed:following:{user_id}"
    ids = cache.lrange(cache_key, cursor, cursor + limit - 1)
    if ids:
        items = [serialize(video) for video in fetch_videos_by_ids(db, ids)]
        return FeedResponse(items=items, next_cursor=str(cursor + limit) if len(ids) == limit else None)

    followees = db.scalars(select(Follow.followee_id).where(Follow.follower_id == UUID(user_id))).all()
    if not followees:
        return FeedResponse(items=[], next_cursor=None)
    videos = db.scalars(
        select(Video)
        .where(Video.author_id.in_(followees), Video.status == VideoStatus.approved)
        .order_by(desc(Video.created_at))
        .limit(limit)
    ).all()
    if videos:
        for video in videos:
            cache.rpush(cache_key, str(video.id))
        cache.ltrim(cache_key, -1000, -1)
        cache.expire(cache_key, 300)
    return FeedResponse(items=[serialize(video) for video in videos], next_cursor=str(cursor + limit) if len(videos) == limit else None)


@app.get("/videos/{video_id}", response_model=VideoResponse)
def get_video(video_id: UUID, _: CurrentUser, db: DbSession) -> Video:
    video = db.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="video not found")
    return video


@app.post("/videos/{video_id}/like")
def toggle_like(video_id: UUID, user_id: CurrentUser, db: DbSession) -> dict[str, bool]:
    existing = db.scalar(select(Like).where(Like.user_id == UUID(user_id), Like.video_id == video_id))
    if existing:
        db.delete(existing)
        db.commit()
        return {"liked": False}
    db.add(Like(user_id=UUID(user_id), video_id=video_id))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
    return {"liked": True}


@app.post("/videos/{video_id}/view")
def record_view(video_id: UUID, user_id: CurrentUser, db: DbSession) -> dict[str, bool]:
    db.add(View(user_id=UUID(user_id), video_id=video_id))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
    return {"recorded": True}


@app.post("/users/{target_user_id}/follow")
def toggle_follow(target_user_id: UUID, user_id: CurrentUser, db: DbSession) -> dict[str, bool]:
    if str(target_user_id) == user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="cannot follow yourself")
    existing = db.scalar(select(Follow).where(Follow.follower_id == UUID(user_id), Follow.followee_id == target_user_id))
    if existing:
        db.delete(existing)
        db.commit()
        return {"following": False}
    db.add(Follow(follower_id=UUID(user_id), followee_id=target_user_id))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
    return {"following": True}


@app.get("/users/{target_user_id}/videos", response_model=list[VideoResponse])
def user_videos(target_user_id: UUID, _: CurrentUser, db: DbSession) -> list[Video]:
    return db.scalars(
        select(Video).where(Video.author_id == target_user_id, Video.status == VideoStatus.approved).order_by(desc(Video.created_at))
    ).all()


@app.post("/internal/videos", response_model=VideoResponse, status_code=status.HTTP_201_CREATED)
def internal_create_video(payload: InternalCreateVideoRequest, db: DbSession, _: InternalAuth) -> Video:
    video = Video(
        id=payload.id,
        author_id=payload.author_id,
        description=payload.description,
        hashtags=payload.hashtags,
        hls_url=payload.hls_url,
        thumbnail_url=payload.thumbnail_url,
        duration=payload.duration,
        status=VideoStatus.moderation_pending,
    )
    video = db.merge(video)
    db.commit()
    db.refresh(video)
    return video


@app.put("/internal/videos/{video_id}/status")
def internal_update_status(video_id: UUID, payload: UpdateStatusRequest, db: DbSession, _: InternalAuth) -> dict[str, str]:
    video = db.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="video not found")
    video.status = payload.status
    db.commit()
    if payload.status == VideoStatus.approved:
        followers = db.scalars(select(Follow.follower_id).where(Follow.followee_id == video.author_id)).all()
        for follower_id in followers:
            cache.lpush(f"feed:following:{follower_id}", str(video.id))
            cache.ltrim(f"feed:following:{follower_id}", 0, 999)
        cache.lpush("feed:foryou", str(video.id))
        cache.ltrim("feed:foryou", 0, 99)
        cache.expire("feed:foryou", 30)
    return {"status": payload.status.value}
