"""Tải & cache robots.txt — tôn trọng chính sách crawl của từng site (lịch sự
là yêu cầu bắt buộc, không phải tuỳ chọn, khi crawl các trang tài chính công khai).
"""

from __future__ import annotations

import httpx
from protego import Protego

from vn_stock_swarm.logging_config import get_logger

logger = get_logger(component="robots")


class RobotsCache:
    """Cache trong bộ nhớ của từng agent, key theo origin, tránh tải lại
    robots.txt mỗi lần gặp URL mới cùng site."""

    def __init__(self, client: httpx.AsyncClient, user_agent: str) -> None:
        self._client = client
        self._user_agent = user_agent
        self._cache: dict[str, Protego] = {}

    async def _get_parser(self, origin: str) -> Protego:
        if origin in self._cache:
            return self._cache[origin]

        robots_url = f"{origin}/robots.txt"
        text = ""
        try:
            resp = await self._client.get(robots_url, timeout=5.0)
            if resp.status_code == 200:
                text = resp.text
        except httpx.HTTPError as exc:
            logger.warning("robots_fetch_failed", url=robots_url, error=str(exc))

        # Không có/không tải được robots.txt → Protego.parse("") coi như "cho
        # phép tất cả", đúng chuẩn robots exclusion (im lặng = không giới hạn).
        parser = Protego.parse(text)
        self._cache[origin] = parser
        return parser

    async def is_allowed(self, url: str, origin: str) -> bool:
        parser = await self._get_parser(origin)
        return parser.can_fetch(url, self._user_agent)
