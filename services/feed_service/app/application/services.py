from datetime import datetime
from uuid import UUID

from redis import Redis

from services.feed_service.app.application.exceptions import InvalidFollowError, VideoNotFoundError
from services.feed_service.app.models import Video, VideoStatus
from services.feed_service.app.repositories import FeedRepository
from services.feed_service.app.schemas import FeedResponse, InternalCreateVideoRequest, UpdateStatusRequest, VideoResponse


class FeedService:
    def __init__(self, repository: FeedRepository, cache: Redis) -> None:
        self.repository = repository
        self.cache = cache

    def for_you(self, *, cursor: str | None, limit: int) -> FeedResponse:
        cache_key = "feed:foryou"
        cached_ids = self.cache.lrange(cache_key, 0, limit - 1)
        if cached_ids:
            items = [self._serialize(video) for video in self.repository.fetch_videos_by_ids(cached_ids)]
            return FeedResponse(items=items, next_cursor=items[-1].created_at.isoformat() if items else None)

        parsed_cursor = datetime.fromisoformat(cursor) if cursor else None
        videos = self.repository.get_approved_for_you(parsed_cursor, limit)
        if videos:
            self.cache.delete(cache_key)
            for video in videos:
                self.cache.rpush(cache_key, str(video.id))
            self.cache.expire(cache_key, 30)
        return FeedResponse(items=[self._serialize(video) for video in videos], next_cursor=videos[-1].created_at.isoformat() if videos else None)

    def following(self, *, user_id: str, cursor: int, limit: int) -> FeedResponse:
        cache_key = f"feed:following:{user_id}"
        ids = self.cache.lrange(cache_key, cursor, cursor + limit - 1)
        if ids:
            items = [self._serialize(video) for video in self.repository.fetch_videos_by_ids(ids)]
            return FeedResponse(items=items, next_cursor=str(cursor + limit) if len(ids) == limit else None)

        videos = self.repository.get_following_feed(UUID(user_id), limit)
        if videos:
            for video in videos:
                self.cache.rpush(cache_key, str(video.id))
            self.cache.ltrim(cache_key, -1000, -1)
            self.cache.expire(cache_key, 300)
        return FeedResponse(items=[self._serialize(video) for video in videos], next_cursor=str(cursor + limit) if len(videos) == limit else None)

    def get_video(self, *, video_id: UUID) -> Video:
        video = self.repository.get_video(video_id)
        if not video:
            raise VideoNotFoundError("video not found")
        return video

    def toggle_like(self, *, video_id: UUID, user_id: str) -> dict[str, bool]:
        return {"liked": self.repository.toggle_like(UUID(user_id), video_id)}

    def record_view(self, *, video_id: UUID, user_id: str) -> dict[str, bool]:
        self.repository.record_view(UUID(user_id), video_id)
        return {"recorded": True}

    def toggle_follow(self, *, target_user_id: UUID, user_id: str) -> dict[str, bool]:
        if str(target_user_id) == user_id:
            raise InvalidFollowError("cannot follow yourself")
        return {"following": self.repository.toggle_follow(UUID(user_id), target_user_id)}

    def user_videos(self, *, target_user_id: UUID) -> list[Video]:
        return self.repository.get_user_videos(target_user_id)

    def internal_create_video(self, payload: InternalCreateVideoRequest) -> Video:
        return self.repository.upsert_video(
            Video(
                id=payload.id,
                author_id=payload.author_id,
                description=payload.description,
                hashtags=payload.hashtags,
                hls_url=payload.hls_url,
                thumbnail_url=payload.thumbnail_url,
                duration=payload.duration,
                status=VideoStatus.moderation_pending,
            )
        )

    def internal_update_status(self, *, video_id: UUID, payload: UpdateStatusRequest) -> dict[str, str]:
        video = self.repository.get_video(video_id)
        if not video:
            raise VideoNotFoundError("video not found")
        video.status = payload.status
        self.repository.commit()
        if payload.status == VideoStatus.approved:
            followers = self.repository.get_follower_ids(video.author_id)
            for follower_id in followers:
                self.cache.lpush(f"feed:following:{follower_id}", str(video.id))
                self.cache.ltrim(f"feed:following:{follower_id}", 0, 999)
            self.cache.lpush("feed:foryou", str(video.id))
            self.cache.ltrim("feed:foryou", 0, 99)
            self.cache.expire("feed:foryou", 30)
        return {"status": payload.status.value}

    def _serialize(self, video: Video) -> VideoResponse:
        return VideoResponse.model_validate(video)
