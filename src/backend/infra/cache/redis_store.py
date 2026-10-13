"""RedisStore cho exact cache. Chỉ get và setex.

Import redis nằm trong __init__ để test và app mặc định không cần gói redis.
"""

from __future__ import annotations

import os
from typing import Any


def redis_url_from_env(url: str | None = None) -> str:
    """Trong Compose dùng redis://redis:6379. Máy host dùng localhost."""
    if url:
        return url
    return os.environ.get("REDIS_URL", "redis://localhost:6379")


class RedisStore:
    def __init__(self, url: str | None = None, client: Any | None = None) -> None:
        if client is not None:
            self._client = client
            return
        import redis

        self._client = redis.from_url(redis_url_from_env(url), decode_responses=True)

    def get(self, key: str) -> str | None:
        return self._client.get(key)

    def setex(self, key: str, ttl_seconds: int, value: str) -> None:
        self._client.setex(key, ttl_seconds, value)
