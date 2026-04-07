from fastapi import FastAPI

from services.moderation_service.app.container import ModerationContainer
from services.moderation_service.app.presentation.routes import router
from services.moderation_service.app.settings import settings
from shared.health import check_database, check_http, readiness_response
from shared.startup import wait_for_database


def create_app() -> FastAPI:
    app = FastAPI(title="Moderation Service")
    container = ModerationContainer.build(settings)
    app.state.container = container
    app.include_router(router)

    @app.on_event("startup")
    def startup() -> None:
        wait_for_database(container.engine, "moderation-service")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"service": "moderation-service", "status": "ok"}

    @app.get("/ready")
    def ready() -> dict[str, object]:
        return readiness_response(
            "moderation-service",
            {
                "database": lambda: check_database(container.engine),
                "feed_service": lambda: check_http(f"{settings.feed_service_url}/health"),
            },
        )

    return app


app = create_app()
