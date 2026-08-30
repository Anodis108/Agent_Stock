"""NewsAgent — 1 trong 5 agent cùng cấp của Sơ đồ 3d, "chỉ search tin".

Chạy ở ĐỢT 1 (song song với PriceAgent + DBAgent). Việc NewsAgent làm và KHÔNG
làm là điểm mấu chốt của Sơ đồ 3d — trước đây (bản chưa tách EvalAgent) 1
agent tin tức thường kiêm luôn việc chấm "tin này tốt hay xấu". Ở đây trách
nhiệm bị cắt rạch ròi:

  1. Gọi Swarm (Sơ đồ 1: publish seed vào stream `scout`) để crawl trang tin
     liên quan tới mã, chờ (poll có timeout) tới khi có tin mới hoặc hết giờ.
  2. Trang crawl về tự động đi qua ContentRouter (Sơ đồ 2 tầng 1) rồi
     SinkRouter (tầng 2, match mã cổ phiếu) NGAY TRONG lúc agent crawl xử lý
     response — đây là cơ chế có sẵn trong BaseCrawlerAgent, NewsAgent không
     phải gọi lại.
  3. Đọc lại tin đã match mã từ bảng STAGING `news_pending` (chưa qua HITL,
     xem sink_store.py) — KHÔNG đọc bảng `news` chính thức, vì bảng đó chỉ
     chứa tin đã được DBAgent commit sau khi người dùng duyệt. Trả về
     NGUYÊN VĂN (title/url/ts), KHÔNG tự chấm tin đó tích cực hay tiêu cực.

Việc "tin này tốt/xấu, đủ tin cậy không, có khớp với biến động giá không" là
của EvalAgent (eval_agent.py) — nó chỉ chạy SAU khi hub đã có cả PriceReport
lẫn NewsReport.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from redis.asyncio import Redis

from config import Settings
from pre_route import stream_name
from query.agents._polling import poll_until
from sink_store import SinkStore

# Seed URL trang tổng hợp tin theo mã — xem ghi chú seed map tương tự ở
# price_agent.py (đủ cho demo, sẽ là 1 registry thật khi triển khai đầy đủ).
_NEWS_SEED_URLS = {
    "VNM": "https://cafef.vn/du-lieu/hose/vnm-cong-ty-co-phan-sua-viet-nam.chn",
    "HPG": "https://cafef.vn/du-lieu/hose/hpg-cong-ty-co-phan-tap-doan-hoa-phat.chn",
    "FPT": "https://cafef.vn/du-lieu/hose/fpt-cong-ty-co-phan-fpt.chn",
    "VCB": "https://cafef.vn/du-lieu/hose/vcb-ngan-hang-tmcp-ngoai-thuong-viet-nam.chn",
}


@dataclass
class NewsReport:
    """Báo cáo NewsAgent gửi về hub — chỉ tin THÔ, chưa có sentiment."""

    symbol: str
    crawled_new: bool  # True nếu lượt này có gọi Swarm crawl thêm (tin cũ chưa đủ mới)
    articles: list[dict[str, object]] = field(default_factory=list)  # title/url/ts thô từ SinkStore
    detail: str = ""


class NewsAgent:
    """Tìm tin liên quan 1 mã cổ phiếu — xem docstring module (KHÔNG chấm sentiment)."""

    def __init__(self, sink_store: SinkStore, redis: Redis, settings: Settings) -> None:
        self._store = sink_store
        self._redis = redis
        self._settings = settings

    async def run(self, symbol: str) -> NewsReport:
        window = self._settings.news_freshness_seconds
        # "Đã có tin gần đây" xét trên CẢ tin đã duyệt lẫn tin đang chờ duyệt
        # — nếu chỉ xét bảng `news` chính thức, NewsAgent sẽ liên tục crawl
        # lại những tin đã tìm thấy nhưng còn đang treo chờ HITL.
        has_recent = await self._store.has_recent_news(
            symbol, window
        ) or await self._store.has_recent_pending_news(symbol, window)

        crawled_new = False
        if not has_recent:
            await self._delegate_crawl(symbol)
            crawled_new = True
            detail = "chưa có tin gần đây → đã gọi Swarm crawl + match mã mới"
        else:
            detail = "đã có tin gần đây (đã duyệt hoặc đang chờ HITL) → dùng luôn, không crawl lại"

        # Gộp tin đã duyệt (news) + tin đang chờ (news_pending): NewsAgent chỉ
        # quan tâm "có tin gì để báo cáo", không quan tâm trạng thái duyệt —
        # đó là việc riêng của DBAgent (prepare_pending_writes so khớp URL để
        # biết tin nào CHƯA từng qua HITL).
        approved = await self._store.recent_news(symbol, window)
        pending = await self._store.recent_pending_news(symbol, window)
        seen_urls: set[str] = set()
        articles: list[dict[str, object]] = []
        for article in [*approved, *pending]:
            url = str(article.get("url", ""))
            if url not in seen_urls:
                seen_urls.add(url)
                articles.append(article)

        return NewsReport(symbol=symbol, articles=articles, crawled_new=crawled_new, detail=detail)

    async def _delegate_crawl(self, symbol: str) -> None:
        url = _NEWS_SEED_URLS.get(symbol)
        if url is None:
            return
        await self._redis.xadd(stream_name("scout"), {"url": url, "depth": "0"})
        await poll_until(
            lambda: self._store.has_recent_pending_news(
                symbol, self._settings.news_freshness_seconds
            ),
            timeout=self._settings.coordinator_poll_timeout_seconds,
            interval=self._settings.coordinator_poll_interval_seconds,
        )
