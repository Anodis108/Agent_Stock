"""Phase 3a — AI service /v1/chat, /v1/scan, /health + steps[]."""

from __future__ import annotations

from fastapi.testclient import TestClient
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles

from src.portfolio_watch.api.deps import AppDeps, set_app_deps
from src.portfolio_watch.ai_main import app
from src.portfolio_watch.domain.entities import WatchlistItem
from src.portfolio_watch.domain.ports import NewsItem, PriceQuote
from src.portfolio_watch.main import app as monolith_app
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
                PriceQuote("FPT", latest_close=105.0, prev_close=100.0)
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


def test_ai_health():
    client = _client()
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data.get("service") == "ai"


def test_ai_v1_chat_returns_answer_and_steps():
    client = _client()
    resp = client.post("/v1/chat", json={"question": "Giá FPT hiện tại?"})
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data and data["answer"]
    assert isinstance(data["steps"], list) and len(data["steps"]) >= 3
    names = [s["name"] for s in data["steps"]]
    assert "rewrite_question" in names
    assert "supervisor" in names
    assert "answer_composer" in names
    for s in data["steps"]:
        assert {"id", "name", "status"} <= set(s.keys())


def test_ai_v1_scan_returns_result_and_steps():
    client = _client()
    resp = client.post("/v1/scan", json={"symbol": "FPT"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "FPT"
    assert "route" in data
    assert isinstance(data["steps"], list) and len(data["steps"]) >= 2
    names = [s["name"] for s in data["steps"]]
    assert "price_agent" in names
    assert "news_agent" in names
    assert data["price"] is not None


def test_ai_app_has_no_static_web_mount():
    """AI process không phục vụ frontend static (Phase 3a)."""
    assert not any(
        isinstance(r, Mount) and isinstance(r.app, StaticFiles) for r in app.routes
    )
    paths = app.openapi()["paths"]
    assert "/v1/chat" in paths
    assert "/v1/scan" in paths
    assert "/health" in paths
    assert not any(p.startswith("/app") for p in paths)
    client = TestClient(app)
    assert client.get("/").status_code == 404
    assert client.get("/app.js").status_code == 404


def test_ai_and_monolith_are_different_apps():
    assert app is not monolith_app
    # Cả hai process API/AI đều không mount static UI
    assert not any(
        isinstance(r, Mount) and isinstance(r.app, StaticFiles)
        for r in monolith_app.routes
    )
