"""SinkStore phải truy vấn được theo mã cổ phiếu và theo độ mới — đây là lý
do nó dùng SQLite thay vì JSONL append-only (xem sink_store.py)."""

from __future__ import annotations

from pathlib import Path

from vn_stock_swarm.sink_store import SinkStore


async def test_save_and_read_price(tmp_path: Path) -> None:
    """Giá vừa lưu phải đọc lại được ngay — tuổi giá gần 0, có trong lịch sử."""
    store = SinkStore(str(tmp_path / "sink.db"))
    await store.save_price("HPG", "https://api.ssi.com.vn/hpg", {"price": "28000"})

    age = await store.latest_price_age_seconds("HPG")
    assert age is not None
    assert age < 5.0

    history = await store.price_history("HPG")
    assert len(history) == 1
    assert history[0]["symbol"] == "HPG"


async def test_latest_price_age_is_none_when_no_data(tmp_path: Path) -> None:
    """Chưa từng lưu giá nào cho mã này → tuổi giá là None, không phải lỗi/exception."""
    store = SinkStore(str(tmp_path / "sink.db"))
    assert await store.latest_price_age_seconds("HPG") is None


async def test_save_news_fans_out_to_every_symbol(tmp_path: Path) -> None:
    """1 tin nhắc nhiều mã phải được lưu 1 bản ghi cho MỖI mã — mỗi mã tra
    cứu tin của riêng nó độc lập."""
    store = SinkStore(str(tmp_path / "sink.db"))
    await store.save_news(["VNM", "HPG"], "VNM và HPG cùng tăng", "https://cafef.vn/a")

    assert await store.has_recent_news("VNM", within_seconds=3600) is True
    assert await store.has_recent_news("HPG", within_seconds=3600) is True
    assert await store.has_recent_news("FPT", within_seconds=3600) is False


async def test_recent_news_respects_freshness_window(tmp_path: Path) -> None:
    """Cửa sổ "gần đây" phải được tôn trọng đúng nghĩa — within_seconds=0
    nghĩa là không có gì đủ mới."""
    store = SinkStore(str(tmp_path / "sink.db"))
    await store.save_news(["HPG"], "Tin cũ", "https://cafef.vn/old")

    assert await store.has_recent_news("HPG", within_seconds=3600) is True
    assert await store.has_recent_news("HPG", within_seconds=0) is False


async def test_save_news_general_does_not_affect_symbol_news(tmp_path: Path) -> None:
    """Tin chung (không match mã nào) phải nằm ở bảng riêng, không lẫn vào
    tin theo mã của bất kỳ mã cụ thể nào."""
    store = SinkStore(str(tmp_path / "sink.db"))
    await store.save_news_general("Ngân hàng Nhà nước điều chỉnh lãi suất", "https://cafef.vn/macro")

    assert await store.has_recent_news("HPG", within_seconds=3600) is False


async def test_pending_news_is_separate_from_official_news(tmp_path: Path) -> None:
    """Tin ở staging (news_pending) không được tính là "tin đã lưu" chính
    thức — đây chính là điểm mấu chốt cho phép HITL của DBAgent có ý nghĩa
    thật (không có gì để duyệt nếu tin đã "chốt" ngay từ lúc crawl)."""
    store = SinkStore(str(tmp_path / "sink.db"))
    await store.save_news_pending(["HPG"], "Tin chưa duyệt", "https://cafef.vn/pending")

    assert await store.has_recent_news("HPG", within_seconds=3600) is False
    assert await store.has_recent_pending_news("HPG", within_seconds=3600) is True


async def test_promote_pending_news_moves_it_to_official_store(tmp_path: Path) -> None:
    """promote_pending_news mô phỏng đúng hành động "HITL duyệt" — sau khi
    gọi, tin phải xuất hiện trong bảng chính thức mà QueryCoordinator dùng."""
    store = SinkStore(str(tmp_path / "sink.db"))
    await store.save_news_pending(["HPG"], "Tin chờ duyệt", "https://cafef.vn/pending")

    await store.promote_pending_news(["HPG"], "Tin chờ duyệt", "https://cafef.vn/pending")

    assert await store.has_recent_news("HPG", within_seconds=3600) is True
