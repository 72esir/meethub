from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from services.auth_service.app.models import SessionModel, User
from services.auth_service.app.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
    UpdateProfileRequest,
    UserResponse,
)
from services.auth_service.app.settings import settings
from shared.api import require_jwt
from shared.db import Base, build_session_factory, get_db
from shared.security import create_access_token, create_refresh_token, hash_password, verify_password
from shared.startup import wait_for_database

app = FastAPI(title="Auth Service")
session_factory = build_session_factory(settings.database_url)
engine = session_factory.kw["bind"]


def db_dependency():
    yield from get_db(session_factory)


CurrentUser = Annotated[str, Depends(require_jwt(settings.jwt_secret))]
DbSession = Annotated[Session, Depends(db_dependency)]


@app.on_event("startup")
def startup() -> None:
    wait_for_database(engine, "auth-service")
    Base.metadata.create_all(bind=engine)


def create_tokens(user: User, db: Session, user_agent: str | None) -> TokenPair:
    refresh_token = create_refresh_token()
    db.add(
        SessionModel(
            user_id=user.id,
            refresh_token=refresh_token,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            user_agent=user_agent,
        )
    )
    db.commit()
    return TokenPair(
        access_token=create_access_token(str(user.id), settings.jwt_secret),
        refresh_token=refresh_token,
    )


@app.post("/auth/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: DbSession, user_agent: Annotated[str | None, Header()] = None) -> TokenPair:
    user = User(email=payload.email, username=payload.username, password_hash=hash_password(payload.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email or username already exists") from exc
    db.refresh(user)
    return create_tokens(user, db, user_agent)


@app.post("/auth/login", response_model=TokenPair)
def login(payload: LoginRequest, db: DbSession, user_agent: Annotated[str | None, Header()] = None) -> TokenPair:
    user = db.scalar(select(User).where(User.email == payload.email))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")
    return create_tokens(user, db, user_agent)


@app.post("/auth/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, db: DbSession, user_agent: Annotated[str | None, Header()] = None) -> TokenPair:
    session = db.scalar(select(SessionModel).where(SessionModel.refresh_token == payload.refresh_token))
    if not session or session.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid refresh token")
    user = db.get(User, session.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    db.delete(session)
    db.commit()
    return create_tokens(user, db, user_agent)


@app.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: RefreshRequest, db: DbSession, _: CurrentUser) -> None:
    session = db.scalar(select(SessionModel).where(SessionModel.refresh_token == payload.refresh_token))
    if session:
        db.delete(session)
        db.commit()


@app.get("/auth/me", response_model=UserResponse)
def me(user_id: CurrentUser, db: DbSession) -> User:
    user = db.get(User, UUID(user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    return user


@app.put("/auth/me", response_model=UserResponse)
def update_me(payload: UpdateProfileRequest, user_id: CurrentUser, db: DbSession) -> User:
    user = db.get(User, UUID(user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    if payload.username is not None:
        user.username = payload.username
    if payload.avatar_url is not None:
        user.avatar_url = payload.avatar_url
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="username already exists") from exc
    db.refresh(user)
    return user
