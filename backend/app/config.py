"""应用配置。"""

from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pydantic import Field, SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class SettingsError(RuntimeError):
    """配置校验失败。"""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("配置校验失败: " + "; ".join(errors))


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
    test_sync_database_url: SecretStr

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


def _format_validation_errors(exc: ValidationError) -> list[str]:
    errors: list[str] = []
    for item in exc.errors(
        include_input=False,
        include_context=False,
        include_url=False,
    ):
        field = ".".join(str(part) for part in item["loc"])
        errors.append(f"{field}: {item['msg']}")
    return errors


def _url_error(
    name: str,
    value: SecretStr,
    schemes: tuple[str, ...],
    *,
    require_database: bool = False,
) -> str | None:
    try:
        parsed = urlparse(value.get_secret_value())
    except ValueError:
        return f"{name}: 不是有效 URL"

    if parsed.scheme not in schemes:
        return f"{name}: 协议必须是 {', '.join(schemes)}"
    if not parsed.hostname:
        return f"{name}: 缺少主机名"
    if require_database and not parsed.path.strip("/"):
        return f"{name}: 缺少数据库名"
    return None


def validate_runtime_settings(settings: Settings) -> Settings:
    """校验启动所需关键配置。"""
    errors: list[str] = []

    database_checks = (
        ("database_url", ("mysql+asyncmy",), True),
        ("sync_database_url", ("mysql+pymysql",), True),
        ("test_database_url", ("mysql+asyncmy",), True),
        ("test_sync_database_url", ("mysql+pymysql",), True),
        ("redis_url", ("redis", "rediss"), False),
        ("celery_broker_url", ("redis", "rediss"), False),
        ("celery_result_backend", ("redis", "rediss"), False),
    )
    for field, schemes, require_database in database_checks:
        value = getattr(settings, field)
        error = _url_error(
            field,
            value,
            schemes,
            require_database=require_database,
        )
        if error:
            errors.append(error)

    if len(settings.jwt_secret_key.get_secret_value()) < 32:
        errors.append("jwt_secret_key: 长度至少为 32")
    if settings.jwt_algorithm != "HS256":
        errors.append("jwt_algorithm: 第一版仅支持 HS256")
    if not 1 <= settings.access_token_expire_minutes <= 1440:
        errors.append("access_token_expire_minutes: 必须在 1 到 1440 之间")

    if not settings.api_prefix.startswith("/") or settings.api_prefix.endswith("/"):
        errors.append("api_prefix: 必须以 / 开头且不能以 / 结尾")
    if not 1 <= settings.smtp_port <= 65535:
        errors.append("smtp_port: 必须在 1 到 65535 之间")
    if settings.smtp_timeout_seconds <= 0:
        errors.append("smtp_timeout_seconds: 必须大于 0")
    if not settings.cors_origins:
        errors.append("cors_origins: 至少需要一个来源")
    for origin in settings.cors_origins:
        parsed_origin = urlparse(origin)
        if parsed_origin.scheme not in {"http", "https"} or not parsed_origin.netloc:
            errors.append("cors_origins: 每项必须是有效的 http/https 来源")
            break
    if settings.app_env == "production" and settings.debug:
        errors.append("debug: 生产环境必须关闭")

    development_db = urlparse(settings.database_url.get_secret_value()).path.strip("/")
    test_db = urlparse(settings.test_database_url.get_secret_value()).path.strip("/")
    if development_db and development_db == test_db:
        errors.append("test_database_url: 测试数据库不能与开发数据库相同")

    test_sync_db = urlparse(
        settings.test_sync_database_url.get_secret_value(),
    ).path.strip("/")
    if test_db and test_sync_db and test_db != test_sync_db:
        errors.append("test_sync_database_url: 必须与异步测试数据库相同")

    if errors:
        raise SettingsError(errors)
    return settings


def load_settings(env_file: Path | None = PROJECT_ROOT / ".env") -> Settings:
    """加载并校验配置。"""
    try:
        settings = Settings(_env_file=env_file)
    except ValidationError as exc:
        raise SettingsError(_format_validation_errors(exc)) from None
    return validate_runtime_settings(settings)
