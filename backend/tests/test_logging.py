import json
import logging
from unittest.mock import patch
from uuid import UUID

import httpx

from app.core.logging import JsonFormatter, request_logger
from app.main import create_app


async def _get(
    path: str,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        return await client.get(path, headers=headers)


async def test_request_ids_are_unique() -> None:
    """每次请求生成唯一 ID。"""
    with patch.object(request_logger, "info"):
        first = await _get("/health")
        second = await _get("/health")

    first_id = first.headers["X-Request-ID"]
    second_id = second.headers["X-Request-ID"]

    UUID(first_id)
    UUID(second_id)
    assert first_id != second_id


async def test_request_log_contains_only_safe_fields() -> None:
    """访问日志不记录凭据和查询串。"""
    with patch.object(request_logger, "info") as log_info:
        response = await _get(
            "/health?password=secret-query",
            headers={"Authorization": "Bearer secret-token"},
        )

    log_info.assert_called_once()
    args, kwargs = log_info.call_args
    extra = kwargs["extra"]
    rendered = json.dumps({"message": args[0], **extra}, ensure_ascii=False)

    assert extra["request_id"] == response.headers["X-Request-ID"]
    assert extra["method"] == "GET"
    assert extra["path"] == "/health"
    assert extra["status_code"] == 200
    assert extra["duration_ms"] >= 0
    assert "secret-token" not in rendered
    assert "secret-query" not in rendered


def test_json_formatter_uses_whitelist() -> None:
    """JSON 格式器只输出固定字段。"""
    record = logging.LogRecord(
        name="ticketflow.request",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="request_completed",
        args=(),
        exc_info=None,
    )
    record.__dict__.update(
        {
            "request_id": "request-1",
            "method": "GET",
            "path": "/health",
            "status_code": 200,
            "duration_ms": 1.25,
            "authorization": "Bearer secret-token",
        },
    )

    payload = json.loads(JsonFormatter().format(record))

    assert payload["request_id"] == "request-1"
    assert payload["method"] == "GET"
    assert payload["path"] == "/health"
    assert payload["status_code"] == 200
    assert payload["duration_ms"] == 1.25
    assert "authorization" not in payload


def test_uvicorn_access_log_is_disabled() -> None:
    """关闭会记录查询串的默认访问日志。"""
    create_app()

    assert logging.getLogger("uvicorn.access").disabled is True
