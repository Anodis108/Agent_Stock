"""Phase 8 — MONITORING_ENABLED=false / thiếu key → chat no-op, không crash."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from src.portfolio_watch.ai_main import app
from src.portfolio_watch.api.deps import AppDeps, set_app_deps
from src.portfolio_watch.domain.entities import WatchlistItem
from src.portfolio_watch.domain.ports import PriceQuote
from src.portfolio_watch.infra.monitoring import tracing as tracing_mod
from src.portfolio_watch.infra.monitoring.tracing import (
    agent_span,
    reset_client_for_tests,
    trace_request,
)
from src.portfolio_watch.shared.settings import settings
from tests.fakes import (
    FakeMemoryStore,
    FakeNewsSource,
    FakeNotifier,
    FakePriceHistoryStore,
    FakePriceSource,
    FakeWatchlistStore,
)


def setup_function():
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
    return TestClient(app)


def test_trace_noop_when_monitoring_disabled(monkeypatch):
    monkeypatch.setattr(settings, "monitoring_enabled", False)
    monkeypatch.setattr(settings, "langfuse_public_key", "pk")
    monkeypatch.setattr(settings, "langfuse_secret_key", "sk")
    with trace_request("chat", "q", metadata={"turn": "t1"}) as root:
        with agent_span("t1", "rewrite_question") as child:
            child["output"] = "x"
        root["output"] = "ok"
    assert tracing_mod._client is None


def test_trace_noop_when_keys_missing(monkeypatch, caplog):
    monkeypatch.setattr(settings, "monitoring_enabled", True)
    monkeypatch.setattr(settings, "langfuse_public_key", None)
    monkeypatch.setattr(settings, "langfuse_secret_key", None)
    with caplog.at_level(logging.WARNING, logger=tracing_mod.__name__):
        with trace_request("chat", "q", metadata={"turn": "t2"}) as box:
            box["output"] = "ok"
    assert tracing_mod._client is None
    assert any("thiếu" in r.message.lower() for r in caplog.records)


def test_trace_noop_when_langfuse_init_fails(monkeypatch, caplog):
    monkeypatch.setattr(settings, "monitoring_enabled", True)
    monkeypatch.setattr(settings, "langfuse_public_key", "pk-bad")
    monkeypatch.setattr(settings, "langfuse_secret_key", "sk-bad")
    monkeypatch.setattr(tracing_mod, "_enabled", lambda: True)
    monkeypatch.setattr(tracing_mod, "_client", None)

    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "langfuse" or name.startswith("langfuse."):
            raise ImportError("langfuse not installed")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with caplog.at_level(logging.WARNING, logger=tracing_mod.__name__):
        with trace_request("chat", "q", metadata={"turn": "t3"}) as box:
            box["output"] = "still-ok"
    assert box.get("output") == "still-ok"
    assert any("init" in r.message.lower() for r in caplog.records)


def test_v1_chat_ok_when_monitoring_disabled(monkeypatch):
    monkeypatch.setattr(settings, "monitoring_enabled", False)
    client = _ai_client()
    resp = client.post("/v1/chat", json={"question": "Giá FPT hiện tại?"})
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("answer")
    assert isinstance(data.get("steps"), list) and len(data["steps"]) >= 1


def test_v1_chat_ok_when_monitoring_on_but_keys_missing(monkeypatch):
    monkeypatch.setattr(settings, "monitoring_enabled", True)
    monkeypatch.setattr(settings, "langfuse_public_key", "")
    monkeypatch.setattr(settings, "langfuse_secret_key", "")
    client = _ai_client()
    resp = client.post("/v1/chat", json={"question": "Giá FPT hiện tại?"})
    assert resp.status_code == 200
    assert resp.json().get("answer")
    assert tracing_mod._client is None


def test_flush_failure_does_not_crash_request(monkeypatch):
    monkeypatch.setattr(settings, "monitoring_enabled", True)
    monkeypatch.setattr(settings, "langfuse_public_key", "pk")
    monkeypatch.setattr(settings, "langfuse_secret_key", "sk")

    root_span = MagicMock()
    fake_lf = MagicMock()
    fake_lf.start_observation = MagicMock(return_value=root_span)
    fake_lf.flush = MagicMock(side_effect=RuntimeError("network"))
    monkeypatch.setattr(tracing_mod, "_get_langfuse", lambda: fake_lf)
    monkeypatch.setattr(tracing_mod, "_client", fake_lf)

    with trace_request("chat", "q", metadata={"turn": "t-flush"}) as box:
        box["output"] = "done"
    # no exception raised
    root_span.end.assert_called()
