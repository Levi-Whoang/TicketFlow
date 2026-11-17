import pytest
from pydantic import SecretStr

from app.config import (
    PROJECT_ROOT,
    Settings,
    SettingsError,
    load_settings,
    validate_runtime_settings,
)
from app.main import create_app


def test_env_example_loads() -> None:
    """示例配置可被统一模型读取。"""
    settings = load_settings(PROJECT_ROOT / ".env.example")

    assert settings.app_name == "TicketFlow"
    assert settings.database_url.get_secret_value().startswith("mysql+asyncmy://")
    assert settings.sync_database_url.get_secret_value().startswith("mysql+pymysql://")
    assert settings.redis_url.get_secret_value().startswith("redis://")
    assert settings.cors_origins == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    assert settings.demo_seed_enabled is True


def test_secret_values_are_masked() -> None:
    """敏感值不会出现在调试字符串中。"""
    settings = Settings(_env_file=PROJECT_ROOT / ".env.example")
    rendered = repr(settings)

    assert "ticketflow:ticketflow" not in rendered
    assert "replace-with-at-least-32-random-characters" not in rendered


def test_missing_critical_config_fails() -> None:
    """缺失关键配置时启动检查失败。"""
    with pytest.raises(SettingsError) as exc_info:
        load_settings(None)

    message = str(exc_info.value)
    assert "database_url" in message
    assert "jwt_secret_key" in message


def test_invalid_secret_is_not_echoed() -> None:
    """校验错误不回显敏感值。"""
    settings = load_settings(PROJECT_ROOT / ".env.example")
    settings.jwt_secret_key = SecretStr("short-secret-value")

    with pytest.raises(SettingsError) as exc_info:
        validate_runtime_settings(settings)

    message = str(exc_info.value)
    assert "jwt_secret_key" in message
    assert "short-secret-value" not in message


def test_test_database_must_differ() -> None:
    """测试库不能与开发库相同。"""
    settings = load_settings(PROJECT_ROOT / ".env.example")
    settings.test_database_url = settings.database_url

    with pytest.raises(SettingsError) as exc_info:
        validate_runtime_settings(settings)

    assert "测试数据库不能与开发数据库相同" in str(exc_info.value)


async def test_app_lifespan_loads_settings() -> None:
    """应用启动时加载配置。"""
    settings = load_settings(PROJECT_ROOT / ".env.example")
    application = create_app(settings)

    async with application.router.lifespan_context(application):
        assert application.state.settings is settings


async def test_app_lifespan_rejects_invalid_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """应用启动时拒绝无效配置。"""

    def fail_load() -> Settings:
        raise SettingsError(["database_url: 缺失"])

    monkeypatch.setattr("app.main.load_settings", fail_load)
    application = create_app()

    with pytest.raises(SettingsError):
        async with application.router.lifespan_context(application):
            pass
