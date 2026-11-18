from typing import Any, cast

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class OrmProbe(BaseModel):
    """测试用 ORM 模型。"""

    __tablename__ = "orm_probe"

    name: Mapped[str] = mapped_column(String(50), nullable=False)


def test_base_model_provides_common_fields() -> None:
    """模型复用主键和时间字段。"""
    table = OrmProbe.__table__

    assert table.c.id.primary_key is True
    assert table.c.id.autoincrement is True
    assert isinstance(table.c.created_at.type, DateTime)
    assert isinstance(table.c.updated_at.type, DateTime)
    assert table.c.created_at.server_default is not None
    assert table.c.updated_at.server_default is not None


def test_constraint_naming_convention_is_applied() -> None:
    """约束使用统一命名。"""
    primary_key = cast(Any, OrmProbe.__table__.primary_key)
    assert primary_key.name == "pk_orm_probe"
