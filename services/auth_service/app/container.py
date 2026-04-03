from dataclasses import dataclass
from typing import Generator

from sqlalchemy.orm import Session, sessionmaker

from services.auth_service.app.application.services import AuthService
from services.auth_service.app.repositories import AuthRepository
from services.auth_service.app.settings import Settings
from shared.db import build_session_factory, get_db


@dataclass(slots=True)
class AuthContainer:
    settings: Settings
    session_factory: sessionmaker[Session]

    @classmethod
    def build(cls, settings: Settings) -> "AuthContainer":
        return cls(settings=settings, session_factory=build_session_factory(settings.database_url))

    @property
    def engine(self):
        return self.session_factory.kw["bind"]

    def get_db(self) -> Generator[Session, None, None]:
        yield from get_db(self.session_factory)

    def auth_service(self, db: Session) -> AuthService:
        return AuthService(repository=AuthRepository(db), jwt_secret=self.settings.jwt_secret)
