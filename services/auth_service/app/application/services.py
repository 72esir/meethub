from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from services.auth_service.app.application.exceptions import (
    InvalidCredentialsError,
    RefreshTokenError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from services.auth_service.app.models import SessionModel, User
from services.auth_service.app.repositories import AuthRepository
from services.auth_service.app.schemas import TokenPair, UpdateProfileRequest
from shared.security import create_access_token, create_refresh_token, hash_password, verify_password


class AuthService:
    def __init__(self, repository: AuthRepository, jwt_secret: str) -> None:
        self.repository = repository
        self.jwt_secret = jwt_secret

    def register(self, *, email: str, password: str, username: str, user_agent: str | None) -> TokenPair:
        user = User(email=email, username=username, password_hash=hash_password(password))
        try:
            user = self.repository.create_user(user)
        except Exception as exc:  # noqa: BLE001
            raise UserAlreadyExistsError("email or username already exists") from exc
        return self._create_tokens(user=user, user_agent=user_agent)

    def login(self, *, email: str, password: str, user_agent: str | None) -> TokenPair:
        user = self.repository.get_user_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError("invalid credentials")
        return self._create_tokens(user=user, user_agent=user_agent)

    def refresh(self, *, refresh_token: str, user_agent: str | None) -> TokenPair:
        session = self.repository.get_session_by_refresh_token(refresh_token)
        if not session or session.expires_at < datetime.now(timezone.utc):
            raise RefreshTokenError("invalid refresh token")
        user = self.repository.get_user(session.user_id)
        if not user:
            raise UserNotFoundError("user not found")
        self.repository.delete_session(session)
        self.repository.commit()
        return self._create_tokens(user=user, user_agent=user_agent)

    def logout(self, *, refresh_token: str) -> None:
        session = self.repository.get_session_by_refresh_token(refresh_token)
        if session:
            self.repository.delete_session(session)
            self.repository.commit()

    def get_me(self, *, user_id: str) -> User:
        user = self.repository.get_user(UUID(user_id))
        if not user:
            raise UserNotFoundError("user not found")
        return user

    def update_me(self, *, user_id: str, payload: UpdateProfileRequest) -> User:
        user = self.repository.get_user(UUID(user_id))
        if not user:
            raise UserNotFoundError("user not found")
        if payload.username is not None:
            user.username = payload.username
        if payload.avatar_url is not None:
            user.avatar_url = payload.avatar_url
        try:
            self.repository.commit()
        except Exception as exc:  # noqa: BLE001
            self.repository.rollback()
            raise UserAlreadyExistsError("username already exists") from exc
        self.repository.refresh(user)
        return user

    def _create_tokens(self, *, user: User, user_agent: str | None) -> TokenPair:
        refresh_token = create_refresh_token()
        self.repository.add_session(
            SessionModel(
                user_id=user.id,
                refresh_token=refresh_token,
                expires_at=datetime.now(timezone.utc) + timedelta(days=30),
                user_agent=user_agent,
            )
        )
        self.repository.commit()
        return TokenPair(
            access_token=create_access_token(str(user.id), self.jwt_secret),
            refresh_token=refresh_token,
        )
