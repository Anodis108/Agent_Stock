"""QueryCoordinator — hub Hierarchical điều phối 5 agent theo đúng 2 đợt của
Sơ đồ 3d, bao gồm luồng dừng-chờ-HITL khi DBAgent có tin mới cần ghi."""

from __future__ import annotations

import time
from pathlib import Path

from config import Settings
from query.agents.db_agent import PendingWrite
from query.agents.news_agent import NewsReport
from query.agents.price_agent import PriceReport
from query.coordinator import QueryCoordinator, TraceStep, _PendingRequest
from sink_store import SinkStore


def _settings(**overrides: object) -> Settings:
    # Timeout nhỏ để test rơi vào nhánh "hết giờ chờ crawl" (không có seed URL
    # đăng ký / không có agent thật đang chạy) vẫn nhanh.
    defaults: dict[str, object] = {
        "coordinator_poll_timeout_seconds": 0.2,
        "coordinator_poll_interval_seconds": 0.05,
        "price_staleness_seconds": 900.0,
        "news_freshness_seconds": 7200.0,
    }
    defaults.update(overrides)
    return Settings(**defaults)


async def test_no_symbol_in_question_returns_early(redis, tmp_path: Path) -> None:
    """Câu hỏi không nhắc mã nào → trả lời ngay, không chạy bất kỳ agent nào cả."""
    store = SinkStore(str(tmp_path / "sink.db"))
    coordinator = QueryCoordinator(store, redis, _settings())

    result = await coordinator.ask("Thị trường hôm nay thế nào?")
    assert result.symbol is None
    assert "Không nhận diện được" in result.answer


async def test_fresh_data_with_no_new_news_answers_immediately(redis, tmp_path: Path) -> None:
    """Giá còn tươi + tin đã có sẵn (không có tin MỚI cần ghi) → trả lời ngay,
    status="answered", không cần dừng chờ HITL."""
    store = SinkStore(str(tmp_path / "sink.db"))
    await store.save_price("HPG", "https://api.ssi.com.vn/hpg", {"close": "28000"})
    await store.save_news(["HPG"], "HPG tăng trần phiên sáng", "https://cafef.vn/hpg-news")

    coordinator = QueryCoordinator(store, redis, _settings())
    result = await coordinator.ask("Giá HPG hôm nay bao nhiêu?")

    assert result.symbol == "HPG"
    assert result.status == "answered"
    # Không có gì mới cần crawl vì cả giá lẫn tin đều đang tươi.
    for agent_type in ("scout", "api"):
        length = await redis.xlen(f"url:discovered:{agent_type}")
        assert length == 0


async def test_all_five_agents_leave_a_trace_step(redis, tmp_path: Path) -> None:
    """Trace phải phản ánh đủ dấu vết của cả 5 agent (Price/News/DB-đọc/Eval/
    Synthesis) — đây là điều Sơ đồ 3d nhấn mạnh: mọi ý trong câu trả lời phải
    truy được về đúng 1 agent."""
    store = SinkStore(str(tmp_path / "sink.db"))
    await store.save_price("HPG", "https://api.ssi.com.vn/hpg", {"close": "28000"})
    await store.save_news(["HPG"], "HPG tăng trần phiên sáng", "https://cafef.vn/hpg-news")

    coordinator = QueryCoordinator(store, redis, _settings())
    result = await coordinator.ask("Giá HPG hôm nay bao nhiêu?")

    steps = {t.step for t in result.trace}
    assert {"price_agent", "news_agent", "db_agent_read", "eval_agent", "synthesis_agent"} <= steps


async def test_stale_price_delegates_a_crawl_via_price_agent(redis, tmp_path: Path) -> None:
    """Giá cũ (chưa từng lưu) → PriceAgent phải publish seed vào stream api,
    hub chỉ điều phối chứ không tự crawl."""
    store = SinkStore(str(tmp_path / "sink.db"))
    await store.save_news(["HPG"], "HPG tăng trần phiên sáng", "https://cafef.vn/hpg-news")

    coordinator = QueryCoordinator(store, redis, _settings())
    result = await coordinator.ask("Giá HPG hôm nay bao nhiêu?")

    assert result.symbol == "HPG"
    length = await redis.xlen("url:discovered:api")
    assert length == 1


async def test_new_pending_news_pauses_for_hitl(redis, tmp_path: Path) -> None:
    """Tin vừa crawl xong (chỉ nằm ở staging `news_pending`, giống hệt những
    gì SinkRouter/crawl-time thật sự làm — xem sink_store.py) nhưng CHƯA có
    trong bảng `news` chính thức → Coordinator phải DỪNG trước Synthesis, trả
    status="pending_approval" kèm request_id + danh sách pending_writes.
    """
    store = SinkStore(str(tmp_path / "sink.db"))
    await store.save_price("HPG", "https://api.ssi.com.vn/hpg", {"close": "28000"})
    # Mô phỏng đúng những gì crawl-time làm: tin theo mã chỉ vào staging.
    await store.save_news_pending(["HPG"], "HPG giảm sàn phiên sáng", "https://cafef.vn/hpg-a")

    coordinator = QueryCoordinator(store, redis, _settings())
    result = await coordinator.ask("Giá HPG hôm nay bao nhiêu?")

    assert result.status == "pending_approval"
    assert result.request_id is not None
    assert len(result.pending_writes) == 1
    assert result.pending_writes[0].url == "https://cafef.vn/hpg-a"


async def test_news_already_approved_does_not_pause_for_hitl(redis, tmp_path: Path) -> None:
    """Tin đã có sẵn trong bảng `news` CHÍNH THỨC (đã qua HITL từ trước) —
    dù NewsAgent vẫn thấy và báo cáo nó, DBAgent không được coi đây là tin
    "mới cần duyệt" nữa, nên Coordinator phải trả lời ngay."""
    store = SinkStore(str(tmp_path / "sink.db"))
    await store.save_price("HPG", "https://api.ssi.com.vn/hpg", {"close": "28000"})
    await store.save_news(["HPG"], "HPG tăng trần phiên sáng", "https://cafef.vn/hpg-old")

    coordinator = QueryCoordinator(store, redis, _settings())
    result = await coordinator.ask("Giá HPG hôm nay bao nhiêu?")

    assert result.status == "answered"


async def test_approve_commits_pending_writes(redis, tmp_path: Path) -> None:
    """resume_after_approval(approve=True) phải thực sự commit tin vào
    SinkStore và trả câu trả lời hoàn chỉnh (status="answered")."""
    store = SinkStore(str(tmp_path / "sink.db"))
    coordinator = QueryCoordinator(store, redis, _settings())

    # Giả lập trạng thái pending trực tiếp qua _pending_requests (đường vòng
    # hợp lệ cho unit test — luồng thật đi qua ask() khi DBAgent phát hiện
    # PendingWrite, xem test_query_api cho luồng end-to-end qua HTTP).
    price = PriceReport(
        symbol="HPG", price_age_seconds=10.0, pct_change=-4.2, used_cache=True, detail=""
    )
    news = NewsReport(symbol="HPG", articles=[], crawled_new=True, detail="")
    pending_write = PendingWrite(
        symbols=["HPG"], title="HPG giảm sàn phiên sáng", url="https://cafef.vn/new"
    )
    coordinator._pending_requests["req-1"] = _PendingRequest(
        symbol="HPG",
        price=price,
        news=news,
        trace=[TraceStep("extract_symbol", "mã: HPG")],
        pending_writes=[pending_write],
        created_at=time.monotonic(),
    )

    result = await coordinator.resume_after_approval("req-1", approve=True)
    assert result is not None
    assert result.status == "answered"
    assert await store.has_recent_news("HPG", within_seconds=3600) is True
    assert "req-1" not in coordinator._pending_requests


async def test_reject_does_not_write_but_still_answers(redis, tmp_path: Path) -> None:
    """resume_after_approval(approve=False) không được ghi gì vào SinkStore,
    nhưng vẫn phải trả về câu trả lời hoàn chỉnh (chỉ log, không chặn user)."""
    store = SinkStore(str(tmp_path / "sink.db"))
    coordinator = QueryCoordinator(store, redis, _settings())

    price = PriceReport(
        symbol="HPG", price_age_seconds=10.0, pct_change=-4.2, used_cache=True, detail=""
    )
    news = NewsReport(symbol="HPG", articles=[], crawled_new=True, detail="")
    pending_write = PendingWrite(
        symbols=["HPG"], title="Tin nghi ngờ", url="https://cafef.vn/reject"
    )
    coordinator._pending_requests["req-2"] = _PendingRequest(
        symbol="HPG",
        price=price,
        news=news,
        trace=[TraceStep("extract_symbol", "mã: HPG")],
        pending_writes=[pending_write],
        created_at=time.monotonic(),
    )

    result = await coordinator.resume_after_approval("req-2", approve=False)
    assert result is not None
    assert result.status == "answered"
    assert await store.has_recent_news("HPG", within_seconds=3600) is False


async def test_unknown_request_id_returns_none(redis, tmp_path: Path) -> None:
    """request_id không tồn tại (sai hoặc đã hết hạn) → None, để api.py trả 404."""
    store = SinkStore(str(tmp_path / "sink.db"))
    coordinator = QueryCoordinator(store, redis, _settings())

    result = await coordinator.resume_after_approval("khong-ton-tai", approve=True)
    assert result is None
