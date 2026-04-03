from fastapi import FastAPI

from services.moderation_service.app.container import ModerationContainer
from services.moderation_service.app.presentation.routes import router
from services.moderation_service.app.settings import settings
from shared.db import Base
from shared.startup import wait_for_database


def create_app() -> FastAPI:
    app = FastAPI(title="Moderation Service")
    container = ModerationContainer.build(settings)
    app.state.container = container
    app.include_router(router)

    @app.on_event("startup")
    def startup() -> None:
        wait_for_database(container.engine, "moderation-service")
        Base.metadata.create_all(bind=container.engine)

    return app


app = create_app()
