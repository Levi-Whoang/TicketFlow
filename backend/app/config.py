"""应用配置。"""

from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """统一读取环境配置。"""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "TicketFlow"
    app_env: Literal["local", "test", "production"] = "local"
    debug: bool = False
    api_prefix: str = "/api/v1"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    database_url: SecretStr
    sync_database_url: SecretStr
    test_database_url: SecretStr

    redis_url: SecretStr
    celery_broker_url: SecretStr
    celery_result_backend: SecretStr

    jwt_secret_key: SecretStr
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    smtp_host: str = "127.0.0.1"
    smtp_port: int = 1025
    smtp_username: str = ""
    smtp_password: SecretStr = SecretStr("")
    smtp_from_email: str = "noreply@ticketflow.local"
    smtp_starttls: bool = False
    smtp_timeout_seconds: int = 10

    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173"],
    )
    demo_seed_enabled: bool = False
