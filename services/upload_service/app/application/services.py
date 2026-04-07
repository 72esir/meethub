from uuid import UUID, uuid4

from redis import Redis

from services.upload_service.app.application.exceptions import UploadNotFoundError
from services.upload_service.app.models import UploadSession, UploadStatus
from services.upload_service.app.repositories import UploadRepository
from services.upload_service.app.schemas import InternalUpdateUploadStatusRequest, LocationPayload, UploadSessionResponse, UploadStatusResponse
from shared.queue import TRANSCODE_QUEUE, enqueue


class UploadService:
    def __init__(self, repository: UploadRepository, queue: Redis, raw_bucket: str, presign_client) -> None:
        self.repository = repository
        self.queue = queue
        self.raw_bucket = raw_bucket
        self.presign_client = presign_client

    def request_upload(self, *, user_id: str, file_name: str, content_type: str) -> UploadSessionResponse:
        upload = UploadSession(user_id=UUID(user_id), s3_key=f"raw/{user_id}/{uuid4()}-{file_name}")
        upload = self.repository.create_upload(upload)
        presigned_url = self.presign_client.generate_presigned_url(
            "put_object",
            Params={"Bucket": self.raw_bucket, "Key": upload.s3_key, "ContentType": content_type},
            ExpiresIn=1800,
        )
        return UploadSessionResponse(upload_id=upload.id, upload_url=presigned_url, s3_key=upload.s3_key)

    def complete_upload(self, *, upload_id: UUID, user_id: str, description: str, hashtags: list[str], location: LocationPayload | None) -> dict[str, str]:
        upload = self.repository.get_upload(upload_id)
        if not upload or str(upload.user_id) != user_id:
            raise UploadNotFoundError("upload not found")
        upload.status = UploadStatus.uploaded
        upload.error_message = None
        upload.description = description
        upload.hashtags = ",".join(hashtags)
        upload.location_name = location.name if location else None
        upload.location_city = location.city if location else None
        upload.location_latitude = location.latitude if location else None
        upload.location_longitude = location.longitude if location else None
        self.repository.commit()
        enqueue(
            self.queue,
            TRANSCODE_QUEUE,
            {
                "upload_id": str(upload.id),
                "user_id": user_id,
                "s3_input_key": upload.s3_key,
                "description": description,
                "hashtags": hashtags,
                "location": location.model_dump() if location else None,
            },
        )
        return {"status": "queued"}

    def get_status(self, *, upload_id: UUID, user_id: str) -> UploadStatusResponse:
        upload = self.repository.get_upload(upload_id)
        if not upload or str(upload.user_id) != user_id:
            raise UploadNotFoundError("upload not found")
        return UploadStatusResponse(
            id=upload.id,
            status=upload.status,
            description=upload.description,
            location=LocationPayload(
                name=upload.location_name,
                city=upload.location_city,
                latitude=upload.location_latitude,
                longitude=upload.location_longitude,
            )
            if any(
                value is not None
                for value in (
                    upload.location_name,
                    upload.location_city,
                    upload.location_latitude,
                    upload.location_longitude,
                )
            )
            else None,
            error_message=upload.error_message,
            hashtags=upload.hashtags.split(",") if upload.hashtags else [],
            created_at=upload.created_at,
        )

    def update_status_internal(self, *, upload_id: UUID, payload: InternalUpdateUploadStatusRequest) -> dict[str, str]:
        upload = self.repository.get_upload(upload_id)
        if not upload:
            raise UploadNotFoundError("upload not found")
        upload.status = payload.status
        upload.error_message = payload.error_message
        self.repository.commit()
        self.repository.refresh(upload)
        return {"status": upload.status.value}
