"""Entrypoint container — chọn 1 trong 5 loại agent qua biến môi trường AGENT_TYPE."""

from __future__ import annotations

import asyncio
import os

from agents import AGENT_CLASSES
from agents.base import run_agent
from config import get_settings
from logging_config import configure_logging, get_logger
from metrics import start_metrics_server


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = get_logger(component="main")

    agent_type = os.environ.get("AGENT_TYPE", "scout")
    agent_class = AGENT_CLASSES.get(agent_type)
    if agent_class is None:
        valid = ", ".join(sorted(AGENT_CLASSES))
        raise SystemExit(f"AGENT_TYPE={agent_type!r} không hợp lệ; phải là một trong: {valid}")

    try:
        start_metrics_server(port=8000)
    except OSError as exc:
        logger.warning("metrics_server_failed", error=str(exc))

    logger.info("starting_agent", agent_type=agent_type)
    asyncio.run(run_agent(agent_class))


if __name__ == "__main__":
    main()
