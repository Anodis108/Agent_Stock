"""PriceAgent — đọc độ mới giá trong SinkStore, gọi Swarm (publish seed) nếu
cũ, tính % biến động. Không tự đọc tin tức, không tự đánh giá gì."""

from __future__ import annotations

from pathlib import Path

from config import Settings
from query.agents.price_agent import PriceAgent
from sink_store import SinkStore


def _settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "coordinator_poll_timeout_seconds": 0.2,
        "coordinator_poll_interval_seconds": 0.05,
        "price_staleness_seconds": 900.0,
    }
    defaults.update(overrides)
    return Settings(**defaults)


async def test_fresh_price_uses_cache_without_crawling(redis, tmp_path: Path) -> None:
    """Giá còn tươi (mới lưu) → không gọi Swarm, dùng luôn dữ liệu có sẵn."""
    store = SinkStore(str(tmp_path / "sink.db"))
    await store.save_price("HPG", "https://api.ssi.com.vn/hpg", {"close": 27000})

    report = await PriceAgent(store, redis, _settings()).run("HPG")
    assert report.used_cache is True
    length = await redis.xlen("url:discovered:api")
    assert length == 0


async def test_stale_price_delegates_a_crawl(redis, tmp_path: Path) -> None:
    """Chưa có giá nào (coi như "cũ vô hạn") → phải publish seed vào stream
    api để Swarm crawl lại, đúng cơ chế Sơ đồ 1."""
    store = SinkStore(str(tmp_path / "sink.db"))

    report = await PriceAgent(store, redis, _settings()).run("HPG")
    assert report.used_cache is False
    length = await redis.xlen("url:discovered:api")
    assert length == 1


async def test_pct_change_computed_from_last_two_prices(redis, tmp_path: Path) -> None:
    """% biến động phải tính từ 2 điểm giá gần nhất trong lịch sử, không phải
    so với giá đầu tiên từng lưu."""
    store = SinkStore(str(tmp_path / "sink.db"))
    await store.save_price("HPG", "https://api.ssi.com.vn/hpg", {"close": 27660})
    await store.save_price("HPG", "https://api.ssi.com.vn/hpg", {"close": 26500})

    report = await PriceAgent(store, redis, _settings()).run("HPG")
    assert report.pct_change is not None
    assert report.pct_change < 0  # 26500 thấp hơn 27660 → % âm (giảm)


async def test_single_price_point_cannot_compute_pct_change(redis, tmp_path: Path) -> None:
    """Chỉ có 1 điểm giá → không đủ dữ liệu để so sánh, pct_change phải là
    None chứ không phải 0 (0% là 1 kết luận có ý nghĩa khác hẳn "chưa biết")."""
    store = SinkStore(str(tmp_path / "sink.db"))
    await store.save_price("HPG", "https://api.ssi.com.vn/hpg", {"close": 27000})

    report = await PriceAgent(store, redis, _settings()).run("HPG")
    assert report.pct_change is None
