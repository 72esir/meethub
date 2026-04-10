from dataclasses import dataclass
from typing import Generator

from redis import Redis
from sqlalchemy.orm import Session, sessionmaker

from services.upload_service.app.application.services import UploadService
from services.upload_service.app.repositories import UploadRepository
from services.upload_service.app.settings import Settings
from shared.db import build_session_factory, get_db
from shared.storage import build_s3_client


@dataclass(slots=True)
class UploadContainer:
    settings: Settings
    session_factory: sessionmaker[Session]
    queue: Redis
    s3_client: object
    presign_s3_client: object

    @classmethod
    def build(cls, settings: Settings) -> "UploadContainer":
        return cls(
            settings=settings,
            session_factory=build_session_factory(settings.database_url),
            queue=Redis.from_url(settings.redis_queue_url, decode_responses=True),
            s3_client=build_s3_client(
                settings.s3_endpoint_url,
                settings.s3_access_key,
                settings.s3_secret_key,
                settings.s3_region,
            ),
            presign_s3_client=build_s3_client(
                settings.s3_public_endpoint_url or settings.s3_endpoint_url,
                settings.s3_access_key,
                settings.s3_secret_key,
                settings.s3_region,
            ),
        )

    @property
    def engine(self):
        return self.session_factory.kw["bind"]

    def get_db(self) -> Generator[Session, None, None]:
        yield from get_db(self.session_factory)

    def upload_service(self, db: Session) -> UploadService:
        return UploadService(
            repository=UploadRepository(db),
            queue=self.queue,
            raw_bucket=self.settings.s3_bucket_raw,
            image_bucket=self.settings.s3_bucket_images,
            cdn_base_url=self.settings.cdn_base_url,
            feed_service_url=self.settings.feed_service_url,
            internal_api_key=self.settings.internal_api_key,
            presign_client=self.presign_s3_client,
        )
