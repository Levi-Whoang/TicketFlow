"""数据库请求依赖。"""

from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession


async def get_async_session(request: Request) -> AsyncIterator[AsyncSession]:
    """提供请求级异步 Session。"""
    try:
        session_factory = request.app.state.async_session_factory
    except AttributeError:
        raise RuntimeError("异步数据库尚未初始化") from None

    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
