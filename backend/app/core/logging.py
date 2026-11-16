"""结构化日志。"""

import json
import logging
from datetime import UTC, datetime
from typing import Any

REQUEST_ID_HEADER = "X-Request-ID"
REQUEST_LOG_FIELDS = (
    "request_id",
    "method",
    "path",
    "status_code",
    "duration_ms",
)

request_logger = logging.getLogger("ticketflow.request")


class JsonFormatter(logging.Formatter):
    """输出固定字段的 JSON 日志。"""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in REQUEST_LOG_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    """配置应用日志。"""
    logger = logging.getLogger("ticketflow")
    logger.setLevel(logging.getLevelNamesMapping().get(level.upper(), logging.INFO))
    logger.propagate = False
    logger.handlers.clear()

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)

    # 使用应用日志，避免默认访问日志泄露查询串。
    logging.getLogger("uvicorn.access").disabled = True
