"""Client Redis dùng chung toàn tiến trình — tránh mỗi agent/route tự mở kết nối riêng."""

from __future__ import annotations

import redis.asyncio as redis

from config import get_settings

_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    """Trả về client Redis bất đồng bộ dùng chung cho cả tiến trình (tạo lười — lazy)."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = redis.from_url(settings.redis_url, decode_responses=True)
    return _client


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
