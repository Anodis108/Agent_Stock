"""Logger ra terminal.

Dùng:
    from app.helper.loging import get_logger
    logger = get_logger(__name__)
    logger.info("hello")
"""

from __future__ import annotations

import logging
import sys

from app.config import settings

_FMT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"


def get_logger(name: str) -> logging.Logger:
    """Trả về logger ghi stdout. Gọi lại cùng `name` không thêm handler trùng."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_FMT, datefmt="%H:%M:%S"))
    logger.addHandler(handler)
    logger.setLevel(settings.log_level.upper())
    logger.propagate = False
    return logger
