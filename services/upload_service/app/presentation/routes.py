from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from services.upload_service.app.application.exceptions import UploadNotFoundError
from services.upload_service.app.application.services import UploadService
from services.upload_service.app.presentation.dependencies import get_current_user, get_upload_service
from services.upload_service.app.schemas import (
    CompleteUploadRequest,
    UploadRequest,
    UploadSessionResponse,
    UploadStatusResponse,
)

router = APIRouter()


@router.post("/upload/request", response_model=UploadSessionResponse)
def request_upload(
    payload: UploadRequest,
    user_id: Annotated[str, Depends(get_current_user)],
    service: Annotated[UploadService, Depends(get_upload_service)],
) -> UploadSessionResponse:
    return service.request_upload(user_id=user_id, file_name=payload.file_name, content_type=payload.content_type)


@router.post("/upload/complete", status_code=status.HTTP_202_ACCEPTED)
def complete_upload(
    payload: CompleteUploadRequest,
    user_id: Annotated[str, Depends(get_current_user)],
    service: Annotated[UploadService, Depends(get_upload_service)],
) -> dict[str, str]:
    try:
        return service.complete_upload(
            upload_id=payload.upload_id,
            user_id=user_id,
            description=payload.description,
            hashtags=payload.hashtags,
        )
    except UploadNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/upload/status/{upload_id}", response_model=UploadStatusResponse)
def upload_status(
    upload_id: UUID,
    user_id: Annotated[str, Depends(get_current_user)],
    service: Annotated[UploadService, Depends(get_upload_service)],
) -> UploadStatusResponse:
    try:
        return service.get_status(upload_id=upload_id, user_id=user_id)
    except UploadNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
