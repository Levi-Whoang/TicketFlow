"""后端应用的标准导入入口。"""

from fastapi import FastAPI

from app import __version__
from app.api.router import api_router
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import register_middleware

APP_NAME = "TicketFlow"


def create_app() -> FastAPI:
    """创建 FastAPI 应用。"""
    configure_logging()
    application = FastAPI(
        title=APP_NAME,
        version=__version__,
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
