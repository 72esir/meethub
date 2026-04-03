from dataclasses import dataclass
from typing import Generator

from redis import Redis
from sqlalchemy.orm import Session, sessionmaker

from services.feed_service.app.application.services import FeedService
from services.feed_service.app.repositories import FeedRepository
from services.feed_service.app.settings import Settings
from shared.db import build_session_factory, get_db


@dataclass(slots=True)
class FeedContainer:
    settings: Settings
    session_factory: sessionmaker[Session]
    cache: Redis

    @classmethod
    def build(cls, settings: Settings) -> "FeedContainer":
        return cls(
            settings=settings,
            session_factory=build_session_factory(settings.database_url),
            cache=Redis.from_url(settings.redis_cache_url, decode_responses=True),
        )

    @property
    def engine(self):
        return self.session_factory.kw["bind"]

    def get_db(self) -> Generator[Session, None, None]:
        yield from get_db(self.session_factory)

    def feed_service(self, db: Session) -> FeedService:
        return FeedService(repository=FeedRepository(db), cache=self.cache)
