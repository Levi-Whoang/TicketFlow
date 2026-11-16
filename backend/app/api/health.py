"""健康检查接口。"""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["健康检查"])


class HealthResponse(BaseModel):
    """健康状态。"""

    status: Literal["ok"] = "ok"


@router.get("/health", response_model=HealthResponse, summary="健康检查")
async def health_check() -> HealthResponse:
    """返回服务状态。"""
    return HealthResponse()
