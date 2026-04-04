from fastapi import FastAPI
from sqlalchemy import text

from services.upload_service.app.container import UploadContainer
from services.upload_service.app.presentation.routes import router
from services.upload_service.app.settings import settings
from shared.db import Base
from shared.health import check_database, check_redis, check_s3, readiness_response
from shared.storage import ensure_bucket
from shared.startup import wait_for_database


def create_app() -> FastAPI:
    app = FastAPI(title="Upload Service")
    container = UploadContainer.build(settings)
    app.state.container = container
    app.include_router(router)

    @app.on_event("startup")
    def startup() -> None:
        wait_for_database(container.engine, "upload-service")
        Base.metadata.create_all(bind=container.engine)
        with container.engine.begin() as connection:
            connection.execute(text("ALTER TABLE upload_sessions ADD COLUMN IF NOT EXISTS error_message TEXT"))
        ensure_bucket(container.s3_client, settings.s3_bucket_raw)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"service": "upload-service", "status": "ok"}

    @app.get("/ready")
    def ready() -> dict[str, object]:
        return readiness_response(
            "upload-service",
            {
                "database": lambda: check_database(container.engine),
                "redis_queue": lambda: check_redis(container.queue),
                "s3": lambda: check_s3(container.s3_client),
            },
        )

    return app


app = create_app()
