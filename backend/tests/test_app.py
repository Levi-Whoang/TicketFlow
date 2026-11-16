from fastapi import FastAPI

from app import __version__
from app.main import APP_NAME, app, create_app


def test_factory_creates_independent_apps() -> None:
    """每次调用都返回独立应用。"""
    first = create_app()
    second = create_app()

    assert isinstance(app, FastAPI)
    assert first is not second
    assert first.title == APP_NAME


def test_app_exposes_openapi_metadata() -> None:
    """应用公开 OpenAPI 信息。"""
    application = create_app()
    schema = application.openapi()

    assert application.docs_url == "/docs"
    assert schema["info"]["title"] == APP_NAME
    assert schema["info"]["version"] == __version__
