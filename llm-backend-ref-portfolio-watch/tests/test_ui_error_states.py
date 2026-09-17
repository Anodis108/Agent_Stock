"""Phase 5 — Frontend: lỗi API hiện rõ, không treo trắng / im lặng."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.portfolio_watch.api.deps import AppDeps, set_app_deps
from src.portfolio_watch.domain.entities import WatchlistItem
from src.portfolio_watch.domain.ports import PriceQuote
from src.portfolio_watch.main import app
from tests.fakes import (
    FakeMemoryStore,
    FakeNewsSource,
    FakeNotifier,
    FakePriceHistoryStore,
    FakePriceSource,
    FakeWatchlistStore,
)


def _client() -> TestClient:
    set_app_deps(
        AppDeps(
            price_source=FakePriceSource(
                PriceQuote("FPT", latest_close=100.0, prev_close=100.0)
            ),
            news_source=FakeNewsSource([[]]),
            history_store=FakePriceHistoryStore([]),
            memory_store=FakeMemoryStore(),
            notifier=FakeNotifier(),
            watchlist_store=FakeWatchlistStore(
                [WatchlistItem(symbol="FPT", threshold_pct=3.0)]
            ),
        )
    )
    return TestClient(app)


def teardown_function():
    set_app_deps(None)


def test_ui_has_error_banner_and_friendly_network_message():
    client = _client()
    html = client.get("/").text
    assert 'id="app-error"' in html
    assert 'role="alert"' in html

    js = client.get("/app.js").text
    assert "Không lấy được dữ liệu, thử lại" in js
    assert "NETWORK_ERROR_MSG" in js
    assert "function showAppError" in js
    assert "function clearAppError" in js
    assert "function formatError" in js
    assert "status === 0" in js
    assert "showAppError(formatError(res" in js
    assert "alert(" not in js

    css = client.get("/style.css").text
    assert ".app-error" in css
    assert "is-visible" in css


def test_ui_scan_chat_errors_go_to_banner_and_panels():
    client = _client()
    scan = client.post("/scan", json={"symbol": ""})
    assert scan.status_code == 400
    assert "detail" in scan.json()

    chat = client.post("/chat", json={"question": "  "})
    assert chat.status_code == 400
    assert "rỗng" in chat.json()["detail"]

    js = client.get("/app.js").text
    assert "showScanResult(null, msg, true)" in js
    assert 'appendChat("assistant", msg)' in js
    assert "showAppError(msg)" in js
    # "Đang quét" không dùng style lỗi
    assert "Đang quét" in js
    assert "showScanResult(null, `Đang quét ${symbol}…`, false)" in js or (
        "Đang quét" in js and "false)" in js
    )


def test_ui_empty_input_shows_error_not_silent():
    client = _client()
    js = client.get("/app.js").text
    assert 'showAppError("symbol rỗng")' in js
    assert 'showAppError("câu hỏi rỗng")' in js


def test_ui_soft_source_errors_surfaced_in_scan_path():
    client = _client()
    js = client.get("/app.js").text
    assert "price.error" in js
    assert "news_error" in js
    assert "showAppError(soft.join" in js
