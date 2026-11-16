"""统一异常和错误响应。"""

from enum import StrEnum
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException


class ErrorCode(StrEnum):
    """标准错误码。"""

    INVALID_REQUEST = "INVALID_REQUEST"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    AUTHORIZATION_DENIED = "AUTHORIZATION_DENIED"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    BUSINESS_CONFLICT = "BUSINESS_CONFLICT"


class ErrorInfo(BaseModel):
    """错误详情。"""

    code: ErrorCode
    message: str
    details: list[dict[str, Any]] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    """统一错误响应。"""

    error: ErrorInfo


class ApiError(Exception):
    """业务异常基类。"""

    def __init__(
        self,
        message: str = "请求无效",
        *,
        code: ErrorCode = ErrorCode.INVALID_REQUEST,
        status_code: int = 400,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or []


class AuthenticationError(ApiError):
    """认证失败。"""

    def __init__(self, message: str = "认证失败") -> None:
        super().__init__(
            message,
            code=ErrorCode.AUTHENTICATION_FAILED,
            status_code=401,
        )


class AuthorizationError(ApiError):
    """权限不足。"""

    def __init__(self, message: str = "没有访问权限") -> None:
        super().__init__(
            message,
            code=ErrorCode.AUTHORIZATION_DENIED,
            status_code=403,
        )


class ResourceNotFoundError(ApiError):
    """资源不存在。"""

    def __init__(self, message: str = "资源不存在") -> None:
        super().__init__(
            message,
            code=ErrorCode.RESOURCE_NOT_FOUND,
            status_code=404,
        )


class BusinessConflictError(ApiError):
    """业务状态冲突。"""

    def __init__(self, message: str = "业务冲突") -> None:
        super().__init__(
            message,
            code=ErrorCode.BUSINESS_CONFLICT,
            status_code=409,
        )


HTTP_ERROR_CODES = {
    400: ErrorCode.INVALID_REQUEST,
    401: ErrorCode.AUTHENTICATION_FAILED,
    403: ErrorCode.AUTHORIZATION_DENIED,
    404: ErrorCode.RESOURCE_NOT_FOUND,
    409: ErrorCode.BUSINESS_CONFLICT,
    422: ErrorCode.VALIDATION_ERROR,
}

HTTP_ERROR_MESSAGES = {
    400: "请求无效",
    401: "认证失败",
    403: "没有访问权限",
    404: "资源不存在",
    409: "业务冲突",
    422: "请求参数校验失败",
}


def _error_response(
    status_code: int,
    code: ErrorCode,
    message: str,
    details: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    payload = ErrorResponse(
        error=ErrorInfo(
            code=code,
            message=message,
            details=details or [],
        ),
    )
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(mode="json"),
    )


def api_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    """处理业务异常。"""
    if not isinstance(exc, ApiError):
        raise exc
    return _error_response(
        exc.status_code,
        exc.code,
        exc.message,
        exc.details,
    )


def validation_error_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    """处理参数校验异常。"""
    if not isinstance(exc, RequestValidationError):
        raise exc
    details = [
        {
            "field": ".".join(str(part) for part in item["loc"]),
            "message": item["msg"],
            "type": item["type"],
        }
        for item in exc.errors()
    ]
    return _error_response(
        422,
        ErrorCode.VALIDATION_ERROR,
        "请求参数校验失败",
        details,
    )


def http_exception_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    """处理标准 HTTP 异常。"""
    if not isinstance(exc, StarletteHTTPException):
        raise exc
    message = HTTP_ERROR_MESSAGES.get(exc.status_code, str(exc.detail))
    code = HTTP_ERROR_CODES.get(exc.status_code, ErrorCode.INVALID_REQUEST)
    return _error_response(exc.status_code, code, message)


def register_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器。"""
    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
