"""初始空迁移。

Revision ID: 1a1c0287ed47
Revises:
Create Date: 2026-11-18 15:24:14.301351

"""

from collections.abc import Sequence

revision: str = "1a1c0287ed47"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """建立迁移基线。"""
    pass


def downgrade() -> None:
    """回滚迁移基线。"""
    pass
