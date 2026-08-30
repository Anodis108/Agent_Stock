"""Helper poll-có-timeout dùng chung cho PriceAgent/NewsAgent khi chờ Swarm
crawl xong — tách riêng vì cả 2 agent đều cần đúng 1 khuôn mẫu này.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


async def poll_until(
    check: Callable[[], Awaitable[T]],
    timeout: float,
    interval: float,
) -> T | None:
    """Poll ``check`` tới khi trả về giá trị truthy hoặc hết ``timeout``.

    Cố tình có giới hạn thời gian, không chờ vô hạn: đây là backend cho 1 demo
    Q&A đồng bộ (user đang chờ HTTP response), nên nếu crawl mất lâu hơn cửa
    sổ chờ thì câu trả lời cứ dùng dữ liệu đã có sẵn — được báo trung thực
    trong trace, không âm thầm giấu đi.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = await check()
        if result:
            return result
        await asyncio.sleep(interval)
    return None
