from uuid import UUID, uuid4

from redis import Redis

from services.upload_service.app.application.exceptions import UploadNotFoundError
from services.upload_service.app.models import UploadSession, UploadStatus
from services.upload_service.app.repositories import UploadRepository
from services.upload_service.app.schemas import UploadSessionResponse, UploadStatusResponse
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

    def complete_upload(self, *, upload_id: UUID, user_id: str, description: str, hashtags: list[str]) -> dict[str, str]:
        upload = self.repository.get_upload(upload_id)
        if not upload or str(upload.user_id) != user_id:
            raise UploadNotFoundError("upload not found")
        upload.status = UploadStatus.uploaded
        upload.description = description
        upload.hashtags = ",".join(hashtags)
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
            hashtags=upload.hashtags.split(",") if upload.hashtags else [],
            created_at=upload.created_at,
        )
