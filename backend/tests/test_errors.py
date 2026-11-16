import json

import httpx
import pytest
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import (
    ApiError,
    AuthenticationError,
    AuthorizationError,
    BusinessConflictError,
    ErrorCode,
    ResourceNotFoundError,
    api_error_handler,
    http_exception_handler,
    validation_error_handler,
)
from app.main import create_app


def _request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "query_string": b"",
        },
    )


async def _raise_conflict() -> None:
    raise BusinessConflictError()


@pytest.mark.parametrize(
    ("error", "status_code", "code"),
    [
        (AuthenticationError(), 401, ErrorCode.AUTHENTICATION_FAILED),
        (AuthorizationError(), 403, ErrorCode.AUTHORIZATION_DENIED),
        (ResourceNotFoundError(), 404, ErrorCode.RESOURCE_NOT_FOUND),
        (BusinessConflictError(), 409, ErrorCode.BUSINESS_CONFLICT),
    ],
)
async def test_api_error_shape(
    error: ApiError,
    status_code: int,
    code: ErrorCode,
) -> None:
    """业务异常使用统一结构。"""
    response = api_error_handler(_request(), error)
    body = json.loads(bytes(response.body).decode())

    assert response.status_code == status_code
    assert body["error"]["code"] == code
    assert body["error"]["details"] == []


async def test_validation_error_shape() -> None:
    """校验异常包含字段级详情。"""
    error = RequestValidationError(
        [
            {
                "type": "int_parsing",
                "loc": ("query", "limit"),
                "msg": "输入必须是整数",
                "input": "bad",
            },
        ],
    )
    response = validation_error_handler(_request(), error)
    body = json.loads(bytes(response.body).decode())

    assert response.status_code == 422
    assert body["error"]["code"] == ErrorCode.VALIDATION_ERROR
    assert body["error"]["details"][0]["field"] == "query.limit"


async def test_http_error_shape() -> None:
    """标准 HTTP 异常使用统一结构。"""
    response = http_exception_handler(
        _request(),
        StarletteHTTPException(status_code=404, detail="Not Found"),
    )
    body = json.loads(bytes(response.body).decode())

    assert response.status_code == 404
    assert body["error"] == {
        "code": ErrorCode.RESOURCE_NOT_FOUND,
        "message": "资源不存在",
        "details": [],
    }


async def test_unknown_path_uses_unified_response() -> None:
    """未知路径返回统一 404。"""
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get("/missing")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == ErrorCode.RESOURCE_NOT_FOUND


async def test_app_registers_api_error_handler() -> None:
    """应用工厂注册业务异常处理器。"""
    application = create_app()
    application.add_api_route("/test-conflict", _raise_conflict)
    transport = httpx.ASGITransport(app=application)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get("/test-conflict")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == ErrorCode.BUSINESS_CONFLICT
