"""DBAgent — ĐỌC luôn tự động, chỉ nhìn bảng `news` CHÍNH THỨC (đã duyệt);
GHI chỉ soạn PendingWrite, KHÔNG commit ngay (commit thật = "thăng cấp" từ
staging sang chính thức, chỉ xảy ra sau khi HITL duyệt qua query/coordinator.py + api.py)."""

from __future__ import annotations

from pathlib import Path

from query.agents.db_agent import DBAgent
from query.agents.news_agent import NewsReport
from sink_store import SinkStore


async def test_read_is_always_automatic(tmp_path: Path) -> None:
    """DBAgent.read() không có tham số/bước duyệt nào — phải chạy và trả kết
    quả ngay, đúng "ĐỌC tự động — không HITL" trong Sơ đồ 3d."""
    store = SinkStore(str(tmp_path / "sink.db"))
    await store.save_price("HPG", "https://api.ssi.com.vn/hpg", {"close": 26500})
    await store.save_news(["HPG"], "HPG tăng trần phiên sáng", "https://cafef.vn/hpg-news")

    result = await DBAgent(store).read("HPG")
    assert len(result.price_history) == 1
    assert len(result.saved_news) == 1


async def test_read_ignores_pending_unapproved_news(tmp_path: Path) -> None:
    """Tin đang ở staging (chưa qua HITL) KHÔNG được tính vào saved_news — đó
    chính là lý do read() không thấy tin đó, nên DBAgent mới soạn được
    PendingWrite cho nó (xem test_prepare_pending_writes_*)."""
    store = SinkStore(str(tmp_path / "sink.db"))
    await store.save_news_pending(["HPG"], "Tin chưa duyệt", "https://cafef.vn/pending")

    result = await DBAgent(store).read("HPG")
    assert result.saved_news == []


async def test_prepare_pending_writes_does_not_touch_the_store(tmp_path: Path) -> None:
    """Soạn lệnh ghi không được ghi bất cứ thứ gì vào bảng `news` chính thức
    — đây là bước ③b "soạn lệnh" trong sơ đồ, tách biệt hoàn toàn khỏi bước
    ④ "COMMIT"."""
    store = SinkStore(str(tmp_path / "sink.db"))
    news = NewsReport(
        symbol="HPG",
        articles=[{"title": "HPG giảm sàn phiên sáng", "url": "https://cafef.vn/a", "ts": 0.0}],
        crawled_new=True,
    )

    pending = DBAgent(store).prepare_pending_writes("HPG", news, already_saved_urls=set())
    assert len(pending) == 1
    assert pending[0].url == "https://cafef.vn/a"
    assert await store.has_recent_news("HPG", within_seconds=3600) is False


async def test_prepare_pending_writes_skips_already_saved_urls(tmp_path: Path) -> None:
    """Tin đã có sẵn trong bảng `news` chính thức (URL trùng) không được soạn
    lại thành lệnh ghi mới — tránh HITL phải duyệt lại thứ đã lưu rồi."""
    store = SinkStore(str(tmp_path / "sink.db"))
    news = NewsReport(
        symbol="HPG",
        articles=[{"title": "Tin cũ", "url": "https://cafef.vn/old", "ts": 0.0}],
        crawled_new=False,
    )

    pending = DBAgent(store).prepare_pending_writes(
        "HPG", news, already_saved_urls={"https://cafef.vn/old"}
    )
    assert pending == []


async def test_commit_pending_writes_promotes_to_official_store(tmp_path: Path) -> None:
    """Chỉ khi commit_pending_writes được gọi (tức đã qua HITL duyệt) thì dữ
    liệu mới thật sự "thăng cấp" vào bảng `news` chính thức."""
    store = SinkStore(str(tmp_path / "sink.db"))
    news = NewsReport(
        symbol="HPG",
        articles=[{"title": "HPG giảm sàn phiên sáng", "url": "https://cafef.vn/a", "ts": 0.0}],
        crawled_new=True,
    )
    agent = DBAgent(store)
    pending = agent.prepare_pending_writes("HPG", news, already_saved_urls=set())

    committed = await agent.commit_pending_writes(pending)
    assert committed == 1
    assert await store.has_recent_news("HPG", within_seconds=3600) is True
