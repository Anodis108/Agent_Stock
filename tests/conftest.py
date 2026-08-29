"""Fixture dùng chung cho toàn bộ test — Redis giả (fakeredis) thay Redis thật,
để test chạy nhanh, không cần hạ tầng, không phụ thuộc mạng."""

from __future__ import annotations

import fakeredis.aioredis
import pytest


@pytest.fixture
async def redis():
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield client
    await client.aclose()
