"""Giới hạn tốc độ theo domain, phân tán qua Redis — mọi agent (bất kể loại
nào, bất kể tiến trình nào) cùng tôn trọng 1 nhịp độ chung cho mỗi domain.
"""

from __future__ import annotations

import asyncio

from redis.asyncio import Redis


class DomainRateLimiter:
    """Limiter kiểu mutex ngắn hạn theo domain (``SET NX PX``), không phải
    token bucket đầy đủ: chiếm được key nghĩa là "tôi giữ lượt request tiếp
    theo cho domain này"; TTL của key chính là khoảng cách tối thiểu giữa 2
    request, nên tự hết hạn, không cần dọn dẹp. Vì trạng thái nằm ở Redis
    (không phải lock trong tiến trình), nó vẫn đúng ngay cả trong khoảnh khắc
    ngắn 2 agent có thể chưa thống nhất ai sở hữu domain (đang đổi thành viên).

    ``pace_multiplier`` lớn hơn 1.0 kéo dài khoảng cách thêm nữa — StealthAgent
    dùng giá trị này để cố tình crawl chậm hơn hẳn, bớt giống bot trên các
    domain từng chặn swarm.
    """

    def __init__(
        self,
        redis: Redis,
        max_requests_per_second: float,
        pace_multiplier: float = 1.0,
    ) -> None:
        self._redis = redis
        base_interval = 1.0 / max_requests_per_second if max_requests_per_second > 0 else 0.0
        self._min_interval = base_interval * pace_multiplier

    async def wait(self, domain: str) -> None:
        if self._min_interval <= 0:
            return
        key = f"ratelimit:{domain}"
        while True:
            acquired = await self._redis.set(
                key, "1", nx=True, px=max(int(self._min_interval * 1000), 1)
            )
            if acquired:
                return
            await asyncio.sleep(self._min_interval / 2)
