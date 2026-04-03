from uuid import UUID

from sqlalchemy.orm import Session

from services.upload_service.app.models import UploadSession


class UploadRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_upload(self, upload: UploadSession) -> UploadSession:
        self.db.add(upload)
        self.db.commit()
        self.db.refresh(upload)
        return upload

    def get_upload(self, upload_id: UUID) -> UploadSession | None:
        return self.db.get(UploadSession, upload_id)

    def commit(self) -> None:
        self.db.commit()
