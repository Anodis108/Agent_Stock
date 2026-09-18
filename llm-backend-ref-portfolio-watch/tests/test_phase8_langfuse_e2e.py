"""Phase 8 — MONITORING on + keys: 1 chat → 1 root + agent spans (UI path)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from backend.main import app as backend_app
from backend.main import store
from backend.store import WatchlistItem as BwItem
from src.portfolio_watch.ai_main import app as ai_app
from src.portfolio_watch.api.deps import AppDeps, set_app_deps
from src.portfolio_watch.domain.entities import WatchlistItem
from src.portfolio_watch.domain.ports import PriceQuote
from src.portfolio_watch.infra.monitoring import tracing as tracing_mod
from src.portfolio_watch.infra.monitoring.tracing import reset_client_for_tests
from src.portfolio_watch.shared.settings import settings
from tests.fakes import (
    FakeMemoryStore,
    FakeNewsSource,
    FakeNotifier,
    FakePriceHistoryStore,
    FakePriceSource,
    FakeWatchlistStore,
)

ROOT = Path(__file__).resolve().parents[1]
FE = ROOT / "frontend"


def setup_function():
    store.clear()
    store.upsert_watchlist(BwItem(symbol="FPT", threshold_pct=3.0))
    reset_client_for_tests()


def teardown_function():
    set_app_deps(None)
    reset_client_for_tests()


def _ai_client() -> TestClient:
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
    return TestClient(ai_app)


def _make_child(names: list[str], name: str) -> Any:
    names.append(name)
    m = MagicMock()
    m.start_observation = MagicMock(return_value=MagicMock())
    m.update = MagicMock()
    m.end = MagicMock()
    return m


def test_frontend_chat_hits_backend_not_ai():
    """UI path: browser → Backend /chat (not AI /v1)."""
    js = (FE / "app.js").read_text(encoding="utf-8")
    assert "/chat" in js
    assert "/v1/chat" not in js


def test_backend_chat_returns_request_id_for_langfuse_correlation(monkeypatch):
    """UI→Backend chat always yields request_id (correlate on Langfuse)."""

    def fake_chat(*, question, user_id="default", request_id=None):
        return {
            "answer": "FPT 105",
            "steps": [
                {"id": "1", "name": "rewrite_question", "status": "done"},
                {"id": "2", "name": "supervisor", "status": "done"},
                {"id": "3", "name": "answer_composer", "status": "done"},
            ],
            "request_id": request_id,
        }

    monkeypatch.setattr("backend.main.ai_chat", fake_chat)
    client = TestClient(backend_app)
    resp = client.post("/chat", json={"question": "Gia FPT?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("answer")
    assert body.get("request_id")
    assert body.get("steps")


def test_ai_chat_with_monitoring_creates_root_and_agent_spans(monkeypatch):
    """AI /v1/chat (Backend proxy target) → 1 root chat + agent child spans."""
    monkeypatch.setattr(settings, "monitoring_enabled", True)
    monkeypatch.setattr(settings, "langfuse_public_key", "pk-test")
    monkeypatch.setattr(settings, "langfuse_secret_key", "sk-test")

    child_names: list[str] = []
    root_span = MagicMock()
    root_span.start_observation = MagicMock(
        side_effect=lambda **kw: _make_child(child_names, kw["name"])
    )
    root_span.update = MagicMock()
    root_span.end = MagicMock()

    fake_lf = MagicMock()
    fake_lf.start_observation = MagicMock(return_value=root_span)
    fake_lf.flush = MagicMock()
    monkeypatch.setattr(tracing_mod, "_get_langfuse", lambda: fake_lf)
    monkeypatch.setattr(tracing_mod, "_client", fake_lf)

    client = _ai_client()
    resp = client.post(
        "/v1/chat",
        json={"question": "Gia FPT hien tai?", "request_id": "ui-corr-1"},
    )
    assert resp.status_code == 200
    assert resp.json().get("answer")
    assert resp.json().get("request_id") == "ui-corr-1"

    fake_lf.start_observation.assert_called()
    assert fake_lf.start_observation.call_args.kwargs["name"] == "chat"
    meta = fake_lf.start_observation.call_args.kwargs.get("metadata") or {}
    assert meta.get("request_id") == "ui-corr-1"
    assert "rewrite_question" in child_names
    assert "supervisor" in child_names
    assert "answer_composer" in child_names
    root_span.end.assert_called()
    fake_lf.flush.assert_called()


@pytest.mark.skipif(
    os.environ.get("PHASE8_LIVE_LANGFUSE", "").strip().lower()
    not in ("1", "true", "yes"),
    reason="Set PHASE8_LIVE_LANGFUSE=1 to hit real Langfuse",
)
def test_live_langfuse_one_chat_has_full_spans():
    """Optional: real Langfuse observations API (same as scripts/phase8_langfuse_e2e)."""
    from scripts.phase8_langfuse_e2e import run_live

    code = run_live()
    assert code == 0
