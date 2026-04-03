from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from services.feed_service.app.models import Follow, Like, Video, VideoStatus, View


class FeedRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def fetch_videos_by_ids(self, ids: list[str]) -> list[Video]:
        if not ids:
            return []
        videos = self.db.scalars(
            select(Video).where(Video.id.in_([UUID(item) for item in ids]), Video.status == VideoStatus.approved)
        ).all()
        order = {video_id: idx for idx, video_id in enumerate(ids)}
        return sorted(videos, key=lambda item: order.get(str(item.id), 0))

    def get_approved_for_you(self, cursor: datetime | None, limit: int) -> list[Video]:
        stmt = select(Video).where(Video.status == VideoStatus.approved)
        if cursor:
            stmt = stmt.where(Video.created_at < cursor)
        return self.db.scalars(stmt.order_by(desc(Video.created_at)).limit(limit)).all()

    def get_following_feed(self, follower_id: UUID, limit: int) -> list[Video]:
        followees = self.db.scalars(select(Follow.followee_id).where(Follow.follower_id == follower_id)).all()
        if not followees:
            return []
        return self.db.scalars(
            select(Video)
            .where(Video.author_id.in_(followees), Video.status == VideoStatus.approved)
            .order_by(desc(Video.created_at))
            .limit(limit)
        ).all()

    def get_video(self, video_id: UUID) -> Video | None:
        return self.db.get(Video, video_id)

    def toggle_like(self, user_id: UUID, video_id: UUID) -> bool:
        existing = self.db.scalar(select(Like).where(Like.user_id == user_id, Like.video_id == video_id))
        if existing:
            self.db.delete(existing)
            self.db.commit()
            return False
        self.db.add(Like(id=uuid4(), user_id=user_id, video_id=video_id))
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
        return True

    def record_view(self, user_id: UUID, video_id: UUID) -> None:
        self.db.add(View(id=uuid4(), user_id=user_id, video_id=video_id))
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()

    def toggle_follow(self, follower_id: UUID, followee_id: UUID) -> bool:
        existing = self.db.scalar(select(Follow).where(Follow.follower_id == follower_id, Follow.followee_id == followee_id))
        if existing:
            self.db.delete(existing)
            self.db.commit()
            return False
        self.db.add(Follow(id=uuid4(), follower_id=follower_id, followee_id=followee_id))
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
        return True

    def get_user_videos(self, target_user_id: UUID) -> list[Video]:
        return self.db.scalars(
            select(Video).where(Video.author_id == target_user_id, Video.status == VideoStatus.approved).order_by(desc(Video.created_at))
        ).all()

    def upsert_video(self, video: Video) -> Video:
        video = self.db.merge(video)
        self.db.commit()
        self.db.refresh(video)
        return video

    def get_follower_ids(self, author_id: UUID) -> list[UUID]:
        return self.db.scalars(select(Follow.follower_id).where(Follow.followee_id == author_id)).all()

    def commit(self) -> None:
        self.db.commit()
