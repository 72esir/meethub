from dataclasses import dataclass
from typing import Generator

from sqlalchemy.orm import Session, sessionmaker

from services.moderation_service.app.application.services import ModerationService
from services.moderation_service.app.repositories import FeedStatusGateway, ModerationRepository
from services.moderation_service.app.settings import Settings
from shared.db import build_session_factory, get_db


@dataclass(slots=True)
class ModerationContainer:
    settings: Settings
    session_factory: sessionmaker[Session]

    @classmethod
    def build(cls, settings: Settings) -> "ModerationContainer":
        return cls(settings=settings, session_factory=build_session_factory(settings.database_url))

    @property
    def engine(self):
        return self.session_factory.kw["bind"]

    def get_db(self) -> Generator[Session, None, None]:
        yield from get_db(self.session_factory)

    def moderation_service(self, db: Session) -> ModerationService:
        return ModerationService(
            repository=ModerationRepository(db),
            feed_gateway=FeedStatusGateway(
                base_url=self.settings.feed_service_url,
                internal_api_key=self.settings.internal_api_key,
            ),
        )
