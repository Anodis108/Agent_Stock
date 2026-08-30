"""Nạp seed URL ban đầu — chạy 1 lần, tự phân loại agent qua pre_route.py rồi
publish thẳng vào đúng stream, y hệt cách 1 agent gossip link mới tìm được."""

from __future__ import annotations

import asyncio

from config import get_settings
from logging_config import configure_logging, get_logger
from pre_route import guess_agent_type, stream_name
from redis_client import close_redis, get_redis


async def load_seeds() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = get_logger(component="seed_loader")

    redis = get_redis()
    seeds = settings.seed_url_list()
    if not seeds:
        logger.warning("no_seed_urls_configured")
        return

    render_domains = settings.render_domain_list()
    for url in seeds:
        agent_type = guess_agent_type(url, render_domains)
        await redis.xadd(stream_name(agent_type), {"url": url, "depth": "0"})
        logger.info("seed_published", url=url, agent_type=agent_type)

    await close_redis()


def main() -> None:
    asyncio.run(load_seeds())


if __name__ == "__main__":
    main()
