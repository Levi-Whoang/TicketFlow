"""Celery 同步数据库设施。"""

from dataclasses import dataclass
from typing import Self

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


@dataclass(slots=True)
class SyncDatabase:
    """持有独立同步 Engine 和 Session 工厂。"""

    engine: Engine
    session_factory: sessionmaker[Session]

    @classmethod
    def create(cls, url: str) -> Self:
        """创建同步数据库设施。"""
        engine = create_engine(
            url,
            pool_pre_ping=True,
            pool_recycle=1800,
        )
        session_factory = sessionmaker(
            bind=engine,
            class_=Session,
            expire_on_commit=False,
            autoflush=False,
        )
        return cls(engine=engine, session_factory=session_factory)

    def dispose(self) -> None:
        """释放连接池。"""
        self.engine.dispose()
