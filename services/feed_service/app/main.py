from fastapi import FastAPI

from services.feed_service.app.container import FeedContainer
from services.feed_service.app.presentation.routes import router
from services.feed_service.app.settings import settings
from shared.health import check_database, check_redis, readiness_response
from shared.startup import wait_for_database


def create_app() -> FastAPI:
    app = FastAPI(title="Feed Service")
    container = FeedContainer.build(settings)
    app.state.container = container
    app.include_router(router)

    @app.on_event("startup")
    def startup() -> None:
        wait_for_database(container.engine, "feed-service")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"service": "feed-service", "status": "ok"}

    @app.get("/ready")
    def ready() -> dict[str, object]:
        return readiness_response(
            "feed-service",
            {
                "database": lambda: check_database(container.engine),
                "redis_cache": lambda: check_redis(container.cache),
            },
        )

    return app


app = create_app()
