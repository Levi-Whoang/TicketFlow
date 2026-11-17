import os
from collections.abc import AsyncGenerator
from types import SimpleNamespace
from typing import Annotated, Self, cast

import httpx
import pytest
from fastapi import Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.database import get_async_session
from app.config import PROJECT_ROOT, load_settings
from app.infrastructure.database import AsyncDatabase
from app.main import create_app


class FakeSession:
    """模拟请求级 Session。"""

    def __init__(self) -> None:
        self.closed = False
        self.rolled_back = False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: object,
        exc: object,
        traceback: object,
    ) -> None:
        self.closed = True

    async def rollback(self) -> None:
        self.rolled_back = True


class FakeSessionFactory:
    """返回模拟 Session。"""

    def __init__(self) -> None:
        self.session = FakeSession()

    def __call__(self) -> FakeSession:
        return self.session


def _request(factory: object | None = None) -> Request:
    state = SimpleNamespace()
    if factory is not None:
        state.async_session_factory = factory
    app = SimpleNamespace(state=state)
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "query_string": b"",
            "app": app,
        },
    )


async def test_session_dependency_closes_on_success() -> None:
    """请求成功后关闭 Session。"""
    factory = FakeSessionFactory()
    dependency = cast(
        AsyncGenerator[AsyncSession, None],
        get_async_session(_request(factory)),
    )

    session = cast(FakeSession, await anext(dependency))
    await dependency.aclose()

    assert session is factory.session
    assert factory.session.closed is True
    assert factory.session.rolled_back is False


async def test_session_dependency_rolls_back_on_error() -> None:
    """请求异常时回滚并关闭 Session。"""
    factory = FakeSessionFactory()
    dependency = cast(
        AsyncGenerator[AsyncSession, None],
        get_async_session(_request(factory)),
    )
    await anext(dependency)

    with pytest.raises(RuntimeError, match="boom"):
        await dependency.athrow(RuntimeError("boom"))

    assert factory.session.closed is True
    assert factory.session.rolled_back is True


async def test_session_dependency_requires_initialization() -> None:
    """未初始化时拒绝创建 Session。"""
    dependency = get_async_session(_request())

    with pytest.raises(RuntimeError, match="异步数据库尚未初始化"):
        await anext(dependency)


async def test_async_database_creates_session_and_disposes() -> None:
    """异步数据库设施创建 Session 工厂并可释放。"""
    settings = load_settings(PROJECT_ROOT / ".env.example")
    database = AsyncDatabase.create(
        settings.database_url.get_secret_value(),
    )

    async with database.session_factory() as session:
        assert isinstance(session, AsyncSession)
        assert session.bind is database.engine

    await database.dispose()


@pytest.mark.skipif(
    os.getenv("RUN_MYSQL_INTEGRATION") != "1",
    reason="需要真实 MySQL",
)
async def test_real_mysql_session_dependency() -> None:
    """真实请求可通过依赖执行 MySQL 查询。"""
    settings = load_settings(PROJECT_ROOT / ".env.example")
    application = create_app(settings)

    async def probe(
        session: Annotated[AsyncSession, Depends(get_async_session)],
    ) -> dict[str, int]:
        result = await session.execute(text("SELECT 1"))
        return {"value": result.scalar_one()}

    application.add_api_route("/db-probe", probe)

    async with application.router.lifespan_context(application):
        transport = httpx.ASGITransport(app=application)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            response = await client.get("/db-probe")

    assert response.status_code == 200
    assert response.json() == {"value": 1}
