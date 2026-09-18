"""Phase 8 — Langfuse: 1 chat/scan = trace cha; bước agent = span con."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from src.portfolio_watch.infra.monitoring import tracing as tracing_mod
from src.portfolio_watch.infra.monitoring.tracing import (
    agent_span,
    reset_client_for_tests,
    trace_request,
)
from src.portfolio_watch.shared.settings import settings


@pytest.fixture(autouse=True)
def _reset_tracing():
    reset_client_for_tests()
    yield
    reset_client_for_tests()


def test_trace_request_noop_when_monitoring_disabled(monkeypatch):
    monkeypatch.setattr(settings, "monitoring_enabled", False)
    with trace_request("chat", "Giá FPT?", metadata={"turn": "t1"}) as box:
        box["output"] = "ok"
        assert box == {"output": "ok"} or "output" in box
    # no client created
    assert tracing_mod._client is None or tracing_mod._client is False


def test_trace_request_and_agent_spans_when_enabled(monkeypatch):
    monkeypatch.setattr(settings, "monitoring_enabled", True)
    monkeypatch.setattr(settings, "langfuse_public_key", "pk-test")
    monkeypatch.setattr(settings, "langfuse_secret_key", "sk-test")

    child_spans: list[str] = []
    root_span = MagicMock()
    root_span.start_observation = MagicMock(
        side_effect=lambda **kw: _make_child(child_spans, kw["name"])
    )

    fake_lf = MagicMock()
    fake_lf.start_observation = MagicMock(return_value=root_span)
    fake_lf.flush = MagicMock()

    monkeypatch.setattr(tracing_mod, "_get_langfuse", lambda: fake_lf)
    # force enabled path without re-init
    monkeypatch.setattr(tracing_mod, "_client", fake_lf)

    with trace_request(
        "chat", "Giá FPT?", metadata={"turn": "turn-a", "kind": "chat"}
    ) as root:
        with agent_span("turn-a", "rewrite_question", input="Giá FPT?") as s1:
            s1["output"] = "rewritten"
        with agent_span("turn-a", "supervisor", input="x") as s2:
            s2["output"] = "price"
        root["output"] = "final"

    fake_lf.start_observation.assert_called_once()
    assert fake_lf.start_observation.call_args.kwargs["name"] == "chat"
    assert "rewrite_question" in child_spans
    assert "supervisor" in child_spans
    root_span.end.assert_called()
    fake_lf.flush.assert_called()


def _make_child(names: list[str], name: str) -> Any:
    names.append(name)
    m = MagicMock()
    m.start_observation = MagicMock(return_value=MagicMock())
    return m


def test_answer_question_still_works_with_monitoring_off(monkeypatch):
    """Regression: chat path không phụ thuộc Langfuse khi tắt monitoring."""
    monkeypatch.setattr(settings, "monitoring_enabled", False)
    from src.portfolio_watch.application.answer_question import answer_question
    from src.portfolio_watch.domain.agents.price_agent import PriceAgentResult
    from src.portfolio_watch.domain.agents.supervisor import (
        RewrittenQuestion,
        RoutingDecision,
    )

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

    def fake_rewrite(q, conv, brain=None):
        return RewrittenQuestion(
            original=q, rewritten=q, symbol="FPT", intent="price_lookup", symbols=["FPT"]
        )

    def fake_route(rewritten, brain=None):
        return RoutingDecision(
            route="price_lookup", reason="test", agents_to_call=["price"]
        )

    def fake_price(sym, src):
        return PriceAgentResult(
            symbol=sym, latest_close=100.0, prev_close=99.0, change_pct=1.0
        )

    monkeypatch.setattr(
        "src.portfolio_watch.application.answer_question.rewrite_question",
        fake_rewrite,
    )
    monkeypatch.setattr(
        "src.portfolio_watch.application.answer_question.route_question",
        fake_route,
    )
    monkeypatch.setattr(
        "src.portfolio_watch.application.answer_question.run_price_agent",
        fake_price,
    )

    def fake_compose(**kwargs):
        from src.portfolio_watch.domain.agents.answer_composer import AnswerComposeResult

        return AnswerComposeResult(
            answer="FPT 100",
            model="test",
            draft_attempts=1,
            guardrail_violations=[],
            evidence=["FPT"],
        )

    monkeypatch.setattr(
        "src.portfolio_watch.application.answer_question.run_answer_composer",
        fake_compose,
    )

    result = answer_question(
        "Giá FPT?",
        price_source=FakePrice(),
        news_source=FakeNews(),
        history_store=FakeHist(),
        memory_store=Mem(),
    )
    assert "FPT" in result.answer
    assert any(s["name"] == "rewrite_question" for s in result.steps)
