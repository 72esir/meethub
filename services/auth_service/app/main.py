from fastapi import FastAPI

from services.auth_service.app.container import AuthContainer
from services.auth_service.app.presentation.routes import router
from services.auth_service.app.settings import settings
from shared.db import Base
from shared.startup import wait_for_database


def create_app() -> FastAPI:
    app = FastAPI(title="Auth Service")
    container = AuthContainer.build(settings)
    app.state.container = container
    app.include_router(router)

    @app.on_event("startup")
    def startup() -> None:
        wait_for_database(container.engine, "auth-service")
        Base.metadata.create_all(bind=container.engine)

    return app


app = create_app()
