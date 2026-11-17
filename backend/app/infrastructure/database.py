"""FastAPI 异步数据库设施。"""

from dataclasses import dataclass
from typing import Self

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


@dataclass(slots=True)
class AsyncDatabase:
    """持有异步 Engine 和 Session 工厂。"""

    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]

    @classmethod
    def create(cls, url: str) -> Self:
        """创建异步数据库设施。"""
        engine = create_async_engine(
            url,
            pool_pre_ping=True,
            pool_recycle=1800,
        )
        session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
        return cls(engine=engine, session_factory=session_factory)

    async def dispose(self) -> None:
        """释放连接池。"""
        await self.engine.dispose()
