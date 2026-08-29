"""Chống crawl trùng — 1 SET Redis dùng chung cho toàn bộ swarm (mọi loại agent)."""

from __future__ import annotations

from redis.asyncio import Redis

VISITED_KEY = "visited:urls"


async def claim_url(redis: Redis, url: str) -> bool:
    """Nhận (claim) 1 URL để crawl, có tính nguyên tử (atomic).

    Trả về True ở lần claim ĐẦU TIÊN (agent gọi hàm này nên tiến hành crawl),
    False ở mọi lần gọi sau đó (đã bị claim rồi — bởi chính agent này hoặc một
    agent khác). ``SADD`` nguyên tử trong Redis nên vẫn an toàn kể cả khi 2
    agent vừa hay race nhau trên cùng 1 URL lúc danh sách thành viên đang đổi.
    """
    # Stub kiểu của redis-py xác định kiểu trả về của sadd() không rõ ràng
    # giữa client đồng bộ/bất đồng bộ; lúc chạy thật luôn là Awaitable[int].
    added = await redis.sadd(VISITED_KEY, url)  # type: ignore[misc]
    return added == 1
