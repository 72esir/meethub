from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from jose import JWTError, jwt
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(subject: str, secret: str, lifetime_minutes: int = 15) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": subject, "iat": int(now.timestamp()), "exp": int((now + timedelta(minutes=lifetime_minutes)).timestamp())}
    return jwt.encode(payload, secret, algorithm="HS256")


def create_refresh_token() -> str:
    return uuid4().hex + uuid4().hex


def decode_token(token: str, secret: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, secret, algorithms=["HS256"])
    except JWTError as exc:
        raise ValueError("invalid token") from exc
