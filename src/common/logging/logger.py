"""Structured Logger with Correlation ID support for VN Stock Swarm."""

from __future__ import annotations

import contextvars
import json
import logging
import sys
from typing import Any

# Context variable lưu trữ correlation_id xuyên suốt async/thread execution
correlation_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default=""
)


def get_correlation_id() -> str:
    return correlation_id_ctx.get()


def set_correlation_id(cid: str) -> None:
    correlation_id_ctx.set(cid)


class CorrelationIdFilter(logging.Filter):
    """Filter gắn correlation_id vào mọi LogRecord."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id() or "-"
        return True


class JsonLogFormatter(logging.Formatter):
    """JSON log formatter cho Production/Cloud logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", "-"),
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj, ensure_ascii=False)


def setup_logging(log_level: str = "INFO", json_format: bool = False) -> None:
    root = logging.getLogger()
    level = getattr(logging, log_level.upper(), logging.INFO)
    root.setLevel(level)

    # Xóa các handler cũ nếu có
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(CorrelationIdFilter())

    if json_format:
        handler.setFormatter(JsonLogFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(correlation_id)s] %(levelname)s [%(name)s] %(message)s"
            )
        )

    root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    # Bảo đảm filter gắn correlation_id luôn có mặt
    if not any(isinstance(f, CorrelationIdFilter) for f in logger.filters):
        logger.addFilter(CorrelationIdFilter())
    return logger
