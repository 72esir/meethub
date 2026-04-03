from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.auth_service.app.models import SessionModel, User


class AuthRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_user(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_user_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email))

    def get_user(self, user_id: UUID) -> User | None:
        return self.db.get(User, user_id)

    def get_session_by_refresh_token(self, refresh_token: str) -> SessionModel | None:
        return self.db.scalar(select(SessionModel).where(SessionModel.refresh_token == refresh_token))

    def add_session(self, session: SessionModel) -> None:
        self.db.add(session)

    def delete_session(self, session: SessionModel) -> None:
        self.db.delete(session)

    def refresh(self, user: User) -> None:
        self.db.refresh(user)

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()
