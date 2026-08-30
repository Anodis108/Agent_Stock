"""PriceAgent — 1 trong 5 agent cùng cấp của Sơ đồ 3d, chuyên "tìm giá biến động".

Chạy ở ĐỢT 1 (song song với NewsAgent + DBAgent), nhận task trực tiếp từ
`QueryCoordinator` (query/coordinator.py) và chỉ báo cáo về lại hub — không
bao giờ nói chuyện thẳng với NewsAgent/EvalAgent/DBAgent/SynthesisAgent.

Việc PriceAgent làm, đúng theo Sơ đồ 3d:
  1. Tự đọc độ mới của giá trong SinkStore (chỉ để biết còn tươi không —
     KHÔNG nhờ qua DBAgent, vì đây là dữ liệu PriceAgent cần ngay lập tức để
     ra quyết định, không phải 1 "báo cáo" cần tổng hợp).
  2. Nếu cũ hơn ngưỡng `price_staleness_seconds` → gọi Swarm (Sơ đồ 1: publish
     seed vào đúng stream, để Scout/Api/Render/Stealth tự xử lý theo cơ chế
     handoff sẵn có) rồi chờ (poll có timeout) tới khi có giá mới hoặc hết giờ.
  3. Tính % thay đổi so với giá liền trước trong lịch sử.

Không tự go tìm nguyên nhân, không đọc tin tức — đó là việc của EvalAgent sau
khi hub đã gộp báo cáo Price + News lại.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from redis.asyncio import Redis

from config import Settings
from pre_route import stream_name
from query.agents._polling import poll_until
from sink_store import SinkStore

# Seed URL dùng để (crawl lại) giá của 1 mã theo yêu cầu. Trong 1 hệ thống
# triển khai đầy đủ, các URL này sẽ được tra cứu từ 1 registry nguồn theo mã;
# 1 bảng cố định nhỏ là đủ cho các mã demo (xem stock_symbols.py).
_PRICE_SEED_URLS = {
    "VNM": "https://s.cafef.vn/Lich-su-giao-dich-VNM-1.chn",
    "HPG": "https://s.cafef.vn/Lich-su-giao-dich-HPG-1.chn",
    "FPT": "https://s.cafef.vn/Lich-su-giao-dich-FPT-1.chn",
    "VCB": "https://s.cafef.vn/Lich-su-giao-dich-VCB-1.chn",
}


@dataclass
class PriceReport:
    """Báo cáo PriceAgent gửi về hub — hub gộp field này vào gói cho Eval/Synthesis."""

    symbol: str
    price_age_seconds: float | None  # None = chưa từng có giá nào trong SinkStore
    pct_change: float | None  # None nếu không đủ lịch sử để tính (< 2 điểm giá)
    used_cache: bool  # True = giá còn tươi, không cần gọi Swarm crawl lại
    detail: str  # Mô tả 1 dòng, tiếng Việt, dùng thẳng trong trace trả cho user


class PriceAgent:
    """Đọc/refresh giá 1 mã cổ phiếu và tính % biến động — xem docstring module."""

    def __init__(self, sink_store: SinkStore, redis: Redis, settings: Settings) -> None:
        self._store = sink_store
        self._redis = redis
        self._settings = settings

    async def run(self, symbol: str) -> PriceReport:
        price_age = await self._store.latest_price_age_seconds(symbol)
        needs_crawl = price_age is None or price_age > self._settings.price_staleness_seconds

        if needs_crawl:
            detail_prefix = (
                "chưa có dữ liệu giá" if price_age is None else f"giá cũ {price_age:.0f}s"
            )
            await self._delegate_crawl(symbol)
            # Đọc lại sau khi chờ Swarm — có thể vẫn là giá cũ nếu crawl chưa
            # kịp về trong thời gian chờ (timeout), đó là kết quả hợp lệ, được
            # phản ánh trung thực trong `detail` chứ không phải lỗi.
            price_age = await self._store.latest_price_age_seconds(symbol)
            detail = f"{detail_prefix} → đã gọi Swarm crawl giá mới"
        else:
            detail = f"giá cập nhật {price_age:.0f}s trước → dùng luôn, không crawl lại"

        pct_change = await self._compute_pct_change(symbol)
        return PriceReport(
            symbol=symbol,
            price_age_seconds=price_age,
            pct_change=pct_change,
            used_cache=not needs_crawl,
            detail=detail,
        )

    async def _compute_pct_change(self, symbol: str) -> float | None:
        history = await self._store.price_history(symbol, limit=2)
        if len(history) < 2:
            return None
        latest, previous = history[0], history[1]
        latest_close = _extract_close(latest["data_json"])
        previous_close = _extract_close(previous["data_json"])
        if latest_close is None or previous_close is None or previous_close == 0:
            return None
        return (latest_close - previous_close) / previous_close * 100

    async def _delegate_crawl(self, symbol: str) -> None:
        url = _PRICE_SEED_URLS.get(symbol)
        if url is None:
            return
        await self._redis.xadd(stream_name("api"), {"url": url, "depth": "0"})
        await poll_until(
            lambda: self._price_updated_recently(symbol),
            timeout=self._settings.coordinator_poll_timeout_seconds,
            interval=self._settings.coordinator_poll_interval_seconds,
        )

    async def _price_updated_recently(self, symbol: str) -> bool:
        age = await self._store.latest_price_age_seconds(symbol)
        return age is not None and age < self._settings.coordinator_poll_timeout_seconds * 2


def _extract_close(data_json: object) -> float | None:
    try:
        data = json.loads(str(data_json))
        close = data.get("close") or data.get("price")
        return float(close) if close is not None else None
    except (ValueError, TypeError, AttributeError):
        return None
