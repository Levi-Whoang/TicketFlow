from app.config import PROJECT_ROOT, Settings


def test_env_example_loads() -> None:
    """示例配置可被统一模型读取。"""
    settings = Settings(_env_file=PROJECT_ROOT / ".env.example")

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
