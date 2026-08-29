"""NewsAgent — chỉ search + gọi Swarm crawl tin, KHÔNG tự chấm sentiment (việc
đó dồn hết cho EvalAgent, xem test_eval_agent.py).

NewsAgent đọc tin từ CẢ bảng `news_pending` (tin vừa crawl, chưa qua HITL) lẫn
`news` (tin đã duyệt) — xem docstring news_agent.py và sink_store.py về lý do
tách 2 bảng này (nếu không, HITL của DBAgent sẽ không bao giờ có gì để duyệt).
"""

from __future__ import annotations

from pathlib import Path

from vn_stock_swarm.config import Settings
from vn_stock_swarm.query.agents.news_agent import NewsAgent
from vn_stock_swarm.sink_store import SinkStore


def _settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "coordinator_poll_timeout_seconds": 0.2,
        "coordinator_poll_interval_seconds": 0.05,
        "news_freshness_seconds": 7200.0,
    }
    defaults.update(overrides)
    return Settings(**defaults)


async def test_recent_pending_news_skips_crawling(redis, tmp_path: Path) -> None:
    """Tin vừa crawl (đang ở staging, chưa duyệt) vẫn tính là "đã có tin gần
    đây" — không cần crawl lại chỉ vì chưa qua HITL."""
    store = SinkStore(str(tmp_path / "sink.db"))
    await store.save_news_pending(["HPG"], "HPG giảm sàn phiên sáng", "https://cafef.vn/a")

    report = await NewsAgent(store, redis, _settings()).run("HPG")
    assert report.crawled_new is False
    assert len(report.articles) == 1


async def test_recent_approved_news_skips_crawling(redis, tmp_path: Path) -> None:
    """Tin đã duyệt từ trước cũng tính là "đã có tin gần đây"."""
    store = SinkStore(str(tmp_path / "sink.db"))
    await store.save_news(["HPG"], "HPG tăng trần phiên sáng", "https://cafef.vn/hpg-news")

    report = await NewsAgent(store, redis, _settings()).run("HPG")
    assert report.crawled_new is False
    assert len(report.articles) == 1


async def test_no_recent_news_delegates_a_crawl(redis, tmp_path: Path) -> None:
    """Không có tin gần đây (cả 2 bảng đều trống) → phải publish seed vào
    stream scout để Swarm crawl."""
    store = SinkStore(str(tmp_path / "sink.db"))

    report = await NewsAgent(store, redis, _settings()).run("HPG")
    assert report.crawled_new is True
    length = await redis.xlen("url:discovered:scout")
    assert length == 1


async def test_articles_merge_pending_and_approved_without_duplicates(
    redis, tmp_path: Path
) -> None:
    """1 tin có mặt ở cả 2 bảng (đã duyệt) không được liệt kê 2 lần trong báo cáo."""
    store = SinkStore(str(tmp_path / "sink.db"))
    await store.save_news_pending(["HPG"], "Tin A", "https://cafef.vn/a")
    await store.save_news(["HPG"], "Tin A", "https://cafef.vn/a")  # cùng URL, đã được duyệt
    await store.save_news_pending(["HPG"], "Tin B", "https://cafef.vn/b")

    report = await NewsAgent(store, redis, _settings()).run("HPG")
    urls = [a["url"] for a in report.articles]
    assert sorted(urls) == ["https://cafef.vn/a", "https://cafef.vn/b"]


async def test_report_never_includes_sentiment_field(redis, tmp_path: Path) -> None:
    """NewsReport chỉ chứa tin thô (title/url/ts) — không có field sentiment
    nào, đúng ranh giới trách nhiệm "chỉ search" của NewsAgent trong Sơ đồ 3d."""
    store = SinkStore(str(tmp_path / "sink.db"))
    await store.save_news_pending(["HPG"], "HPG giảm sàn phiên sáng", "https://cafef.vn/a")

    report = await NewsAgent(store, redis, _settings()).run("HPG")
    for article in report.articles:
        assert "sentiment" not in article
