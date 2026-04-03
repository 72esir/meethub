from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status

from services.auth_service.app.application.exceptions import (
    InvalidCredentialsError,
    RefreshTokenError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from services.auth_service.app.application.services import AuthService
from services.auth_service.app.presentation.dependencies import get_auth_service, get_current_user
from services.auth_service.app.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
    UpdateProfileRequest,
    UserResponse,
)

router = APIRouter()


@router.post("/auth/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
    user_agent: Annotated[str | None, Header()] = None,
) -> TokenPair:
    try:
        return service.register(email=payload.email, password=payload.password, username=payload.username, user_agent=user_agent)
    except UserAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/auth/login", response_model=TokenPair)
def login(
    payload: LoginRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
    user_agent: Annotated[str | None, Header()] = None,
) -> TokenPair:
    try:
        return service.login(email=payload.email, password=payload.password, user_agent=user_agent)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.post("/auth/refresh", response_model=TokenPair)
def refresh(
    payload: RefreshRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
    user_agent: Annotated[str | None, Header()] = None,
) -> TokenPair:
    try:
        return service.refresh(refresh_token=payload.refresh_token, user_agent=user_agent)
    except (RefreshTokenError, UserNotFoundError) as exc:
        status_code = status.HTTP_401_UNAUTHORIZED if isinstance(exc, RefreshTokenError) else status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    payload: RefreshRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
    _: Annotated[str, Depends(get_current_user)],
) -> None:
    service.logout(refresh_token=payload.refresh_token)


@router.get("/auth/me", response_model=UserResponse)
def me(
    user_id: Annotated[str, Depends(get_current_user)],
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    try:
        return service.get_me(user_id=user_id)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.put("/auth/me", response_model=UserResponse)
def update_me(
    payload: UpdateProfileRequest,
    user_id: Annotated[str, Depends(get_current_user)],
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    try:
        return service.update_me(user_id=user_id, payload=payload)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except UserAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
