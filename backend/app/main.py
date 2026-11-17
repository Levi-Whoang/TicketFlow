"""后端应用的标准导入入口。"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import __version__
from app.api.router import api_router
from app.config import Settings, load_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import register_middleware
from app.infrastructure.database import AsyncDatabase

APP_NAME = "TicketFlow"


def create_app(settings: Settings | None = None) -> FastAPI:
    """创建 FastAPI 应用。"""
    configure_logging(settings.log_level if settings else "INFO")

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        runtime_settings = settings or load_settings()
        application.state.settings = runtime_settings
        configure_logging(runtime_settings.log_level)
        database = AsyncDatabase.create(
            runtime_settings.database_url.get_secret_value(),
        )
        application.state.async_database = database
        application.state.async_session_factory = database.session_factory
        try:
            yield
        finally:
            await database.dispose()

    application = FastAPI(
        title=APP_NAME,
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    register_middleware(application)
    register_exception_handlers(application)
    application.include_router(api_router)
    return application


app = create_app()

__all__ = ["APP_NAME", "app", "create_app"]
