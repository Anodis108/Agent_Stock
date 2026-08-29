from __future__ import annotations

import itertools

import httpx

from vn_stock_swarm.agents.base import BaseCrawlerAgent
from vn_stock_swarm.config import Settings
from vn_stock_swarm.fetcher import RawResponse, fetch_page


class StealthAgent(BaseCrawlerAgent):
    """Agent cứu cánh cuối cùng cho các domain đã chặn swarm nhiều lần liên
    tiếp (403/429/CAPTCHA — xem nhánh BLOCKED_REPEATEDLY trong handoff.py).
    Handoff vào loại agent này chuyển giao CẢ DOMAIN, không chỉ 1 URL
    (``handoff.HandoffDecision.handoff_whole_domain``), vì 1 site đã chặn 1
    request thì nhiều khả năng cũng chặn request kế tiếp từ cùng fingerprint.

    Biện pháp giảm nhẹ cố tình ở mức khiêm tốn cho project học tập: xoay vòng
    proxy (nếu có cấu hình — danh sách rỗng nghĩa là "không dùng proxy, chỉ
    dựa vào việc giảm tốc") và giảm tốc độ request đáng kể. Không giải
    CAPTCHA, không giả lập fingerprint gì thêm ngoài User-Agent mặc định —
    mục tiêu là 1 crawler lịch sự, kiên nhẫn, không phải né tránh phát hiện
    một cách chủ động.
    """

    agent_type = "stealth"

    def __init__(self, settings: Settings | None = None, agent_id: str | None = None) -> None:
        super().__init__(settings, agent_id)
        proxies = self.settings.stealth_proxy_list()
        self._proxy_cycle = itertools.cycle(proxies) if proxies else None

    def rate_limiter_pace_multiplier(self) -> float:
        return self.settings.stealth_pace_multiplier

    async def fetch(self, client: httpx.AsyncClient, url: str) -> RawResponse | None:
        if self._proxy_cycle is None:
            return await fetch_page(client, url)

        proxy = next(self._proxy_cycle)
        async with httpx.AsyncClient(
            headers=client.headers, timeout=client.timeout, proxy=proxy
        ) as proxied_client:
            return await fetch_page(proxied_client, url)
