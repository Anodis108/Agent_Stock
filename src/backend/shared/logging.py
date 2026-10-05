from __future__ import annotations

import logging
import sys


def setup_logging(log_level: str = "INFO") -> None:
    root = logging.getLogger()
    if root.handlers:
        root.setLevel(log_level.upper())
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    )
    root.addHandler(handler)
    root.setLevel(log_level.upper())


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
