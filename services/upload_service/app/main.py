from typing import Annotated
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, HTTPException, status
from redis import Redis
from sqlalchemy.orm import Session

from services.upload_service.app.models import UploadSession, UploadStatus
from services.upload_service.app.schemas import (
    CompleteUploadRequest,
    UploadRequest,
    UploadSessionResponse,
    UploadStatusResponse,
)
from services.upload_service.app.settings import settings
from shared.api import require_jwt
from shared.db import Base, build_session_factory, get_db
from shared.queue import TRANSCODE_QUEUE, enqueue
from shared.storage import build_s3_client, ensure_bucket

app = FastAPI(title="Upload Service")
session_factory = build_session_factory(settings.database_url)
engine = session_factory.kw["bind"]
s3_client = build_s3_client(
    settings.s3_endpoint_url,
    settings.s3_access_key,
    settings.s3_secret_key,
    settings.s3_region,
)
queue = Redis.from_url(settings.redis_queue_url, decode_responses=True)


def db_dependency():
    yield from get_db(session_factory)


DbSession = Annotated[Session, Depends(db_dependency)]
CurrentUser = Annotated[str, Depends(require_jwt(settings.jwt_secret))]


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_bucket(s3_client, settings.s3_bucket_raw)


@app.post("/upload/request", response_model=UploadSessionResponse)
def request_upload(payload: UploadRequest, user_id: CurrentUser, db: DbSession) -> UploadSessionResponse:
    upload = UploadSession(user_id=UUID(user_id), s3_key=f"raw/{user_id}/{uuid4()}-{payload.file_name}")
    db.add(upload)
    db.commit()
    db.refresh(upload)
    presigned_url = s3_client.generate_presigned_url(
        "put_object",
        Params={"Bucket": settings.s3_bucket_raw, "Key": upload.s3_key, "ContentType": payload.content_type},
        ExpiresIn=1800,
    )
    return UploadSessionResponse(upload_id=upload.id, upload_url=presigned_url, s3_key=upload.s3_key)


@app.post("/upload/complete", status_code=status.HTTP_202_ACCEPTED)
def complete_upload(payload: CompleteUploadRequest, user_id: CurrentUser, db: DbSession) -> dict[str, str]:
    upload = db.get(UploadSession, payload.upload_id)
    if not upload or str(upload.user_id) != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="upload not found")
    upload.status = UploadStatus.uploaded
    upload.description = payload.description
    upload.hashtags = ",".join(payload.hashtags)
    db.commit()
    enqueue(
        queue,
        TRANSCODE_QUEUE,
        {
            "upload_id": str(upload.id),
            "user_id": user_id,
            "s3_input_key": upload.s3_key,
            "description": payload.description,
            "hashtags": payload.hashtags,
        },
    )
    return {"status": "queued"}


@app.get("/upload/status/{upload_id}", response_model=UploadStatusResponse)
def upload_status(upload_id: UUID, user_id: CurrentUser, db: DbSession) -> UploadStatusResponse:
    upload = db.get(UploadSession, upload_id)
    if not upload or str(upload.user_id) != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="upload not found")
    return UploadStatusResponse(
        id=upload.id,
        status=upload.status,
        description=upload.description,
        hashtags=upload.hashtags.split(",") if upload.hashtags else [],
        created_at=upload.created_at,
    )
