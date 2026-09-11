from __future__ import annotations

import httpx

from agents.base import BaseCrawlerAgent
from fetcher import RawResponse
from render_fetcher import fetch_rendered_page


class RenderAgent(BaseCrawlerAgent):
    """Agent dùng trình duyệt headless cho bảng giá SPA nặng JavaScript (vd
    bảng giá real-time của công ty chứng khoán, render hoàn toàn phía client).
    Vào tới đây trực tiếp (domain của URL nằm trong RENDER_DOMAINS) hoặc qua
    handoff từ ScoutAgent (đã phát hiện shell SPA rỗng khi GET thuần).
    """

    agent_type = "render"

    async def fetch(self, client: httpx.AsyncClient, url: str) -> RawResponse | None:
        return await fetch_rendered_page(
            url, self.settings.user_agent, self.settings.fetch_timeout_seconds
        )
