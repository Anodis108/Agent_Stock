"""Phase 8 — request_id Backend → AI → Langfuse metadata."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from backend.main import app, store
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


def setup_function():
    store.clear()
    from backend.store import WatchlistItem as BwItem

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


def test_backend_chat_generates_and_forwards_request_id(monkeypatch):
    seen: dict[str, Any] = {}

    def fake_chat(*, question, user_id="default", request_id=None):
        seen["request_id"] = request_id
        seen["question"] = question
        return {
            "answer": "FPT 105",
            "steps": [
                {"id": "1", "name": "rewrite_question", "status": "done"},
                {"id": "2", "name": "supervisor", "status": "done"},
                {"id": "3", "name": "answer_composer", "status": "done"},
            ],
            "question": question,
            "symbol": "FPT",
            "route": "price_lookup",
            "request_id": request_id,
        }

    monkeypatch.setattr("backend.main.ai_chat", fake_chat)
    client = TestClient(app)
    resp = client.post("/chat", json={"question": "Giá FPT?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("request_id")
    assert seen["request_id"] == body["request_id"]


def test_backend_scan_generates_and_forwards_request_id(monkeypatch):
    seen: dict[str, Any] = {}

    def fake_scan(*, symbol, user_id="default", threshold_pct=None, request_id=None):
        seen["request_id"] = request_id
        return {
            "symbol": symbol,
            "route": "normal",
            "steps": [],
            "reason": "",
            "threshold_pct": threshold_pct or 3.0,
            "request_id": request_id,
            "price": {
                "symbol": symbol,
                "latest_close": 100.0,
                "prev_close": 99.0,
                "change_pct": 1.0,
                "error": None,
            },
            "news_count": 0,
            "news": [],
            "pending_events": [],
        }

    monkeypatch.setattr("backend.main.ai_scan", fake_scan)
    client = TestClient(app)
    resp = client.post("/scan", json={"symbol": "FPT"})
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("request_id")
    assert seen["request_id"] == body["request_id"]


def test_ai_v1_chat_echoes_request_id_from_body():
    client = _ai_client()
    rid = "req-from-backend-001"
    resp = client.post(
        "/v1/chat",
        json={"question": "Giá FPT hiện tại?", "request_id": rid},
    )
    assert resp.status_code == 200
    assert resp.json()["request_id"] == rid


def test_ai_v1_chat_accepts_x_request_id_header():
    client = _ai_client()
    rid = "hdr-req-002"
    resp = client.post(
        "/v1/chat",
        json={"question": "Giá FPT hiện tại?"},
        headers={"X-Request-Id": rid},
    )
    assert resp.status_code == 200
    assert resp.json()["request_id"] == rid


def test_answer_question_puts_request_id_in_langfuse_metadata(monkeypatch):
    monkeypatch.setattr(settings, "monitoring_enabled", True)
    monkeypatch.setattr(settings, "langfuse_public_key", "pk-test")
    monkeypatch.setattr(settings, "langfuse_secret_key", "sk-test")

    captured: dict[str, Any] = {}
    root_span = MagicMock()
    root_span.start_observation = MagicMock(return_value=MagicMock())
    fake_lf = MagicMock()
    fake_lf.start_observation = MagicMock(return_value=root_span)
    fake_lf.flush = MagicMock()
    monkeypatch.setattr(tracing_mod, "_get_langfuse", lambda: fake_lf)
    monkeypatch.setattr(tracing_mod, "_client", fake_lf)

    def capture_start(**kwargs):
        captured["metadata"] = kwargs.get("metadata")
        return root_span

    fake_lf.start_observation.side_effect = capture_start

    from src.portfolio_watch.application.answer_question import answer_question
    from src.portfolio_watch.domain.agents.answer_composer import AnswerComposeResult
    from src.portfolio_watch.domain.agents.price_agent import PriceAgentResult
    from src.portfolio_watch.domain.agents.supervisor import RewrittenQuestion
    from src.portfolio_watch.domain.entities import RoutingDecision

    class Mem:
        def list_conversation(self, *a, **k):
            return []

        def list_alert_events(self, *a, **k):
            return []

        def append_conversation(self, *a, **k):
            return None

        def append_alert_event(self, *a, **k):
            return None

    class FakePrice:
        def get_latest(self, symbol):
            return None

    class FakeNews:
        def search(self, *a, **k):
            return []

    class FakeHist:
        def get_closes(self, *a, **k):
            return []

        def append(self, *a, **k):
            return None

    monkeypatch.setattr(
        "src.portfolio_watch.application.answer_question.rewrite_question",
        lambda q, conv, brain=None: RewrittenQuestion(
            original=q,
            rewritten=q,
            symbol="FPT",
            intent="price_lookup",
            symbols=["FPT"],
        ),
    )
    monkeypatch.setattr(
        "src.portfolio_watch.application.answer_question.route_question",
        lambda rewritten, brain=None: RoutingDecision(
            route="price_lookup", reason="test", agents_to_call=["price"]
        ),
    )
    monkeypatch.setattr(
        "src.portfolio_watch.application.answer_question.run_price_agent",
        lambda sym, src: PriceAgentResult(
            symbol=sym, latest_close=100.0, prev_close=99.0, change_pct=1.0
        ),
    )
    monkeypatch.setattr(
        "src.portfolio_watch.application.answer_question.run_answer_composer",
        lambda **kwargs: AnswerComposeResult(
            answer="FPT 100",
            model="test",
            draft_attempts=1,
            guardrail_violations=[],
            evidence=["FPT"],
        ),
    )

    rid = "corr-id-xyz"
    result = answer_question(
        "Giá FPT?",
        price_source=FakePrice(),
        news_source=FakeNews(),
        history_store=FakeHist(),
        memory_store=Mem(),
        request_id=rid,
    )
    assert "FPT" in result.answer
    meta = captured.get("metadata") or {}
    assert meta.get("request_id") == rid
    assert meta.get("turn") == rid


def test_ai_client_includes_request_id_in_payload_and_header(monkeypatch):
    from backend import ai_client

    captured: dict[str, Any] = {}

    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b'{"ok": true}'

    def fake_urlopen(req, timeout=None):
        captured["headers"] = dict(req.headers)
        captured["body"] = req.data.decode("utf-8")
        return FakeResp()

    monkeypatch.setattr(ai_client.urllib.request, "urlopen", fake_urlopen)
    out = ai_client.ai_chat(question="Giá FPT?", request_id="rid-abc")
    assert out["ok"] is True
    assert '"request_id": "rid-abc"' in captured["body"]
    # urllib normalizes header keys
    hdrs = {k.lower(): v for k, v in captured["headers"].items()}
    assert hdrs.get("x-request-id") == "rid-abc"
