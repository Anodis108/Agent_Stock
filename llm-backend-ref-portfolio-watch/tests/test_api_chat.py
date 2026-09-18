from __future__ import annotations

from fastapi.testclient import TestClient

from src.portfolio_watch.api.deps import AppDeps, set_app_deps
from src.portfolio_watch.application.review_approval import list_pending_approvals
from src.portfolio_watch.domain.entities import WatchlistItem
from src.portfolio_watch.domain.ports import NewsItem, PriceQuote
from src.portfolio_watch.main import app
from tests.fakes import (
    FakeMemoryStore,
    FakeNewsSource,
    FakeNotifier,
    FakePriceHistoryStore,
    FakePriceSource,
    FakeWatchlistStore,
)


def _client(
    *,
    latest: float = 105.0,
    prev: float = 100.0,
    news_batches: list | None = None,
) -> tuple[TestClient, FakeMemoryStore]:
    mem = FakeMemoryStore()
    set_app_deps(
        AppDeps(
            price_source=FakePriceSource(
                PriceQuote("FPT", latest_close=latest, prev_close=prev)
            ),
            news_source=FakeNewsSource(news_batches or [[]]),
            history_store=FakePriceHistoryStore([]),
            memory_store=mem,
            notifier=FakeNotifier(),
            # product-spec / test-plan #5: hỏi về mã trong watchlist
            watchlist_store=FakeWatchlistStore(
                [WatchlistItem(symbol="FPT", threshold_pct=3.0)]
            ),
        )
    )
    return TestClient(app), mem


def teardown_function():
    set_app_deps(None)


def test_post_chat_price_lookup():
    """test-plan #5: hỏi giá 1 mã trong watchlist → trả lời, không HITL."""
    client, mem = _client()
    resp = client.post("/chat", json={"question": "Giá FPT hiện tại?"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "FPT"
    assert data["agents_to_call"] == ["price"]
    assert "eval" not in data["agents_to_call"]
    assert data["hitl_used"] is False
    assert data["pending_approvals_created"] == 0
    assert data["price"] is not None
    assert data["price"]["change_pct"] == 5.0
    assert data["news_error"] is None
    assert "105" in data["answer"] or "5.00" in data["answer"]
    assert mem.alert_events == []
    assert list_pending_approvals(mem) == []
    assert len(mem.list_conversation("default")) >= 2
    steps = data["steps"]
    assert isinstance(steps, list) and len(steps) >= 3
    names = [s["name"] for s in steps]
    assert names[0] == "rewrite_question"
    assert "supervisor" in names
    assert "price_agent" in names
    assert "answer_composer" in names
    for s in steps:
        assert set(s) >= {"id", "name", "status"}
        assert s["status"] in ("done", "error", "pending", "running")


def test_post_chat_explain_with_news():
    """test-plan #6: tại sao giảm → có tin/lý do cụ thể, không HITL."""
    news = [NewsItem(title="FPT giảm do tin xấu", snippet="giảm", symbol="FPT")]
    client, mem = _client(latest=95.0, prev=100.0, news_batches=[news])
    resp = client.post("/chat", json={"question": "Tại sao giá FPT giảm?"})
    assert resp.status_code == 200
    data = resp.json()
    assert "eval" in data["agents_to_call"]
    assert "news" in data["agents_to_call"]
    assert data["severity"] is not None
    assert data["news_count"] >= 1
    assert data["news_error"] is None
    assert any("FPT" in (n.get("title") or "") for n in data["news"])
    assert "tin" in data["answer"].lower() or "giảm" in data["answer"].lower()
    assert data["hitl_used"] is False
    assert data["pending_approvals_created"] == 0
    assert mem.alert_events == []
    assert list_pending_approvals(mem) == []


def test_post_chat_followup_uses_memory():
    """product-spec Luồng 2 + Supervisor: follow-up dùng lịch sử hội thoại."""
    client, mem = _client()
    first = client.post("/chat", json={"question": "Xem giúp mã FPT"})
    assert first.status_code == 200
    assert first.json()["symbol"] == "FPT"

    second = client.post("/chat", json={"question": "Còn mã đó thì sao?"})
    assert second.status_code == 200
    data = second.json()
    assert data["symbol"] == "FPT"
    assert data["hitl_used"] is False
    assert list_pending_approvals(mem) == []
    assert len(mem.list_conversation("default")) >= 4


def test_post_chat_empty_question_400():
    client, _ = _client()
    resp = client.post("/chat", json={"question": ""})
    assert resp.status_code == 400
    assert "rỗng" in resp.json()["detail"]


def test_post_chat_whitespace_question_400():
    client, _ = _client()
    resp = client.post("/chat", json={"question": "   "})
    assert resp.status_code == 400
    assert "rỗng" in resp.json()["detail"]
