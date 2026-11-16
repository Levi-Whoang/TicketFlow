"""中间件注册。"""

from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.core.logging import REQUEST_ID_HEADER, request_logger


class RequestContextMiddleware(BaseHTTPMiddleware):
    """生成请求 ID 并记录访问日志。"""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        request_id = str(uuid4())
        request.state.request_id = request_id
        started_at = perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            _log_request(request_id, request, 500, started_at)
            raise

        response.headers[REQUEST_ID_HEADER] = request_id
        _log_request(request_id, request, response.status_code, started_at)
        return response


def _log_request(
    request_id: str,
    request: Request,
    status_code: int,
    started_at: float,
) -> None:
    request_logger.info(
        "request_completed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": status_code,
            "duration_ms": round((perf_counter() - started_at) * 1000, 2),
        },
    )


def register_middleware(app: FastAPI) -> None:
    """挂载应用中间件。"""
    app.add_middleware(RequestContextMiddleware)
