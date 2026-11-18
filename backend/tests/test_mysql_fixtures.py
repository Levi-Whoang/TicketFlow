from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session


async def test_async_mysql_fixture_starts_clean(
    async_mysql_session: AsyncSession,
) -> None:
    """异步测试开始前清理探针数据。"""
    result = await async_mysql_session.execute(
        text("SELECT COUNT(*) FROM _ticketflow_fixture_probe"),
    )
    assert result.scalar_one() == 0

    await async_mysql_session.execute(
        text(
            "INSERT INTO _ticketflow_fixture_probe (id, value) VALUES (1, 'async')",
        ),
    )
    await async_mysql_session.commit()


async def test_async_mysql_fixture_cleans_previous_data(
    async_mysql_session: AsyncSession,
) -> None:
    """后续异步测试不继承前一个测试数据。"""
    result = await async_mysql_session.execute(
        text("SELECT COUNT(*) FROM _ticketflow_fixture_probe"),
    )
    assert result.scalar_one() == 0


def test_sync_mysql_fixture_starts_clean(
    sync_mysql_session: Session,
) -> None:
    """同步测试开始前清理探针数据。"""
    result = sync_mysql_session.execute(
        text("SELECT COUNT(*) FROM _ticketflow_fixture_probe"),
    )
    assert result.scalar_one() == 0

    sync_mysql_session.execute(
        text(
            "INSERT INTO _ticketflow_fixture_probe (id, value) VALUES (2, 'sync')",
        ),
    )
    sync_mysql_session.commit()


def test_sync_mysql_fixture_cleans_after_test(
    sync_mysql_session: Session,
) -> None:
    """同步测试不继承前一个测试数据。"""
    result = sync_mysql_session.execute(
        text("SELECT COUNT(*) FROM _ticketflow_fixture_probe"),
    )
    assert result.scalar_one() == 0
