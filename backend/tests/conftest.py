from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from urllib.parse import urlparse

import pytest
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from alembic import command
from app.config import Settings, load_settings
from app.infrastructure.database import AsyncDatabase
from app.infrastructure.sync_database import SyncDatabase

BACKEND_ROOT = Path(__file__).resolve().parents[1]
TEST_DATABASE_NAME = "ticketflow_test"
PROBE_TABLE = "_ticketflow_fixture_probe"


def _database_name(url: str) -> str:
    return urlparse(url).path.strip("/")


async def _reset_async_database(
    database: AsyncDatabase,
    expected_name: str,
) -> None:
    async with database.engine.begin() as connection:
        current_name = (await connection.execute(text("SELECT DATABASE()"))).scalar_one()
        if current_name != expected_name:
            raise RuntimeError("拒绝清理非测试数据库")

        await connection.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        try:
            result = await connection.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = DATABASE() "
                    "AND table_type = 'BASE TABLE'",
                ),
            )
            for (table_name,) in result:
                if table_name != "alembic_version":
                    escaped = table_name.replace("`", "``")
                    await connection.execute(
                        text(f"TRUNCATE TABLE `{escaped}`"),
                    )
        finally:
            await connection.execute(text("SET FOREIGN_KEY_CHECKS=1"))


def _reset_sync_database(
    database: SyncDatabase,
    expected_name: str,
) -> None:
    with database.engine.begin() as connection:
        current_name = connection.execute(text("SELECT DATABASE()")).scalar_one()
        if current_name != expected_name:
            raise RuntimeError("拒绝清理非测试数据库")

        connection.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        try:
            result = connection.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = DATABASE() "
                    "AND table_type = 'BASE TABLE'",
                ),
            )
            for (table_name,) in result:
                if table_name != "alembic_version":
                    escaped = table_name.replace("`", "``")
                    connection.execute(text(f"TRUNCATE TABLE `{escaped}`"))
        finally:
            connection.execute(text("SET FOREIGN_KEY_CHECKS=1"))


@pytest.fixture(scope="session")
def mysql_test_settings() -> Settings:
    """加载并确认真实 MySQL 测试库配置。"""
    settings = load_settings()
    async_name = _database_name(
        settings.test_database_url.get_secret_value(),
    )
    sync_name = _database_name(
        settings.test_sync_database_url.get_secret_value(),
    )

    assert async_name == TEST_DATABASE_NAME
    assert sync_name == TEST_DATABASE_NAME
    return settings


@pytest.fixture(scope="session")
def migrated_mysql_test_database(
    mysql_test_settings: Settings,
) -> Iterator[None]:
    """迁移测试库并管理探针表。"""
    alembic_config = Config(str(BACKEND_ROOT / "alembic.ini"))
    database_url = mysql_test_settings.test_sync_database_url.get_secret_value()
    alembic_config.set_main_option(
        "sqlalchemy.url",
        database_url.replace("%", "%%"),
    )
    command.upgrade(alembic_config, "head")

    database = SyncDatabase.create(database_url)
    try:
        with database.engine.begin() as connection:
            connection.execute(
                text(
                    f"CREATE TABLE IF NOT EXISTS `{PROBE_TABLE}` "
                    "(id INT PRIMARY KEY, value VARCHAR(32) NOT NULL)",
                ),
            )
        yield
    finally:
        with database.engine.begin() as connection:
            connection.execute(text(f"DROP TABLE IF EXISTS `{PROBE_TABLE}`"))
        database.dispose()


@pytest.fixture
async def async_mysql_session(
    mysql_test_settings: Settings,
    migrated_mysql_test_database: None,
) -> AsyncIterator[AsyncSession]:
    """提供干净的真实 MySQL 异步 Session。"""
    database = AsyncDatabase.create(
        mysql_test_settings.test_database_url.get_secret_value(),
    )
    await _reset_async_database(database, TEST_DATABASE_NAME)
    try:
        async with database.session_factory() as session:
            yield session
    finally:
        await _reset_async_database(database, TEST_DATABASE_NAME)
        await database.dispose()


@pytest.fixture
def sync_mysql_session(
    mysql_test_settings: Settings,
    migrated_mysql_test_database: None,
) -> Iterator[Session]:
    """提供干净的真实 MySQL 同步 Session。"""
    database = SyncDatabase.create(
        mysql_test_settings.test_sync_database_url.get_secret_value(),
    )
    _reset_sync_database(database, TEST_DATABASE_NAME)
    try:
        with database.session_factory() as session:
            yield session
    finally:
        _reset_sync_database(database, TEST_DATABASE_NAME)
        database.dispose()
