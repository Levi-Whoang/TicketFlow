"""Alembic 迁移环境。"""

from logging.config import fileConfig

from sqlalchemy import create_engine, pool

from alembic import context
from app import models
from app.config import load_settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = load_settings()
database_url = settings.sync_database_url.get_secret_value()
config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
target_metadata = models.Base.metadata


def run_migrations_offline() -> None:
    """离线生成迁移 SQL。"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """连接数据库执行迁移。"""
    connectable = create_engine(
        database_url,
        poolclass=pool.NullPool,
    )

    try:
        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
            )

            with context.begin_transaction():
                context.run_migrations()
    finally:
        connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
