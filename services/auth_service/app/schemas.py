from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    username: str = Field(min_length=3, max_length=64)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UpdateProfileRequest(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=64)
    avatar_url: str | None = None


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    username: str
    avatar_url: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
