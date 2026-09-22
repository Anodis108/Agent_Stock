"""Langfuse tracing — mock hierarchy parent/child, 1 request = 1 trace, no-op when disabled."""

from __future__ import annotations

from typing import Any
import pytest
from fastapi.testclient import TestClient

from src.portfolio_watch.ai_main import app
from src.portfolio_watch.application.answer_question import answer_question
from src.portfolio_watch.application.scan_symbol import scan_symbol
from src.portfolio_watch.infra.monitoring import tracing as tracing_mod
from src.portfolio_watch.infra.monitoring.tracing import reset_client_for_tests, trace_request
from src.portfolio_watch.shared.settings import settings


class MockObservation:
    def __init__(
        self,
        name: str,
        as_type: str = "span",
        input: Any = None,
        metadata: dict[str, Any] | None = None,
        parent: MockObservation | None = None,
        model: str | None = None,
    ):
        self.name = name
        self.as_type = as_type
        self.input = input
        self.metadata = dict(metadata or {})
        self.parent = parent
        self.model = model
        self.children: list[MockObservation] = []
        self.output: Any = None
        self.ended: bool = False
        self.level: str | None = None
        self.status_message: str | None = None

    def start_observation(self, **kwargs) -> MockObservation:
        child = MockObservation(
            name=kwargs.get("name", ""),
            as_type=kwargs.get("as_type", "span"),
            input=kwargs.get("input"),
            metadata=kwargs.get("metadata"),
            parent=self,
            model=kwargs.get("model"),
        )
        self.children.append(child)
        return child

    def update(self, **kwargs) -> None:
        if "output" in kwargs:
            self.output = kwargs["output"]
        if "level" in kwargs:
            self.level = kwargs["level"]
        if "status_message" in kwargs:
            self.status_message = kwargs["status_message"]
        if "metadata" in kwargs and isinstance(kwargs["metadata"], dict):
            self.metadata.update(kwargs["metadata"])

    def end(self) -> None:
        self.ended = True


class MockLangfuse:
    def __init__(self):
        self.roots: list[MockObservation] = []
        self.flushed: bool = False

    def start_observation(self, **kwargs) -> MockObservation:
        root = MockObservation(
            name=kwargs.get("name", ""),
            as_type=kwargs.get("as_type", "agent"),
            input=kwargs.get("input"),
            metadata=kwargs.get("metadata"),
            parent=None,
        )
        self.roots.append(root)
        return root

    def flush(self) -> None:
        self.flushed = True


@pytest.fixture(autouse=True)
def _reset_tracing():
    reset_client_for_tests()
    yield
    reset_client_for_tests()


@pytest.fixture
def mock_langfuse(monkeypatch):
    """Kích hoạt monitoring với mock client để kiểm tra hierarchy mà không cần host thật."""
    monkeypatch.setattr(settings, "monitoring_enabled", True)
    monkeypatch.setattr(settings, "langfuse_public_key", "pk-mock-test")
    monkeypatch.setattr(settings, "langfuse_secret_key", "sk-mock-test")
    monkeypatch.setattr(settings, "langfuse_host", "http://mock-langfuse:3000")
    client = MockLangfuse()
    monkeypatch.setattr(tracing_mod, "_client", client)
    return client


def test_trace_noop_when_disabled(monkeypatch):
    monkeypatch.setattr(settings, "monitoring_enabled", False)
    with trace_request("chat", "q", metadata={"turn": "t1"}) as box:
        box["output"] = "ok"
    assert tracing_mod._client is None


def test_v1_chat_ok_when_monitoring_off(real_deps, monkeypatch):
    monkeypatch.setattr(settings, "monitoring_enabled", False)
    resp = TestClient(app).post("/v1/chat", json={"question": "Giá FPT?"})
    assert resp.status_code == 200 and resp.json().get("answer")


def test_chat_single_root_and_hierarchy(real_deps, mock_langfuse):
    """Đúng 1 root 'chat', child agent spans dưới root, steps lồng dưới agent span tương ứng."""
    res = answer_question(
        "Giá FPT hôm nay thế nào?",
        price_source=real_deps.price_source,
        news_source=real_deps.news_source,
        history_store=real_deps.history_store,
        memory_store=real_deps.memory_store,
    )
    assert res.answer

    # 1. Đúng 1 root trace
    assert len(mock_langfuse.roots) == 1, f"Kỳ vọng đúng 1 root trace, nhận {len(mock_langfuse.roots)}"
    root = mock_langfuse.roots[0]
    assert root.name == "chat"
    assert root.ended is True
    assert root.parent is None
    assert root.input == "Giá FPT hôm nay thế nào?"
    assert root.output == res.answer

    # 2. Child agent spans dưới root
    child_names = [c.name for c in root.children]
    assert "rewrite_question" in child_names
    assert "supervisor" in child_names
    assert "price_agent" in child_names
    assert "answer_composer" in child_names

    for span in root.children:
        assert span.parent is root, f"Span {span.name} phải có parent là root trace"
        assert span.ended is True, f"Span {span.name} chưa gọi end()"
        assert span.input is not None, f"Span {span.name} thiếu input"
        assert span.output is not None, f"Span {span.name} thiếu output"

    # 3. Hierarchy nesting: step con lồng dưới agent span đúng
    rewrite_span = next(c for c in root.children if c.name == "rewrite_question")
    rewrite_steps = [s.name for s in rewrite_span.children]
    assert "rewrite" in rewrite_steps
    step_rw = next(s for s in rewrite_span.children if s.name == "rewrite")
    assert step_rw.parent is rewrite_span
    assert step_rw.input is not None
    assert step_rw.output is not None

    supervisor_span = next(c for c in root.children if c.name == "supervisor")
    supervisor_steps = [s.name for s in supervisor_span.children]
    assert "route" in supervisor_steps
    step_route = next(s for s in supervisor_span.children if s.name == "route")
    assert step_route.parent is supervisor_span
    assert step_route.input is not None
    assert step_route.output is not None

    price_span = next(c for c in root.children if c.name == "price_agent")
    price_steps = [s.name for s in price_span.children]
    assert "fetch_quote" in price_steps
    step_quote = next(s for s in price_span.children if s.name == "fetch_quote")
    assert step_quote.parent is price_span
    assert step_quote.input is not None
    assert step_quote.output is not None

    composer_span = next(c for c in root.children if c.name == "answer_composer")
    composer_steps = [s.name for s in composer_span.children]
    assert "draft" in composer_steps
    step_draft = next(s for s in composer_span.children if s.name == "draft")
    assert step_draft.parent is composer_span
    assert step_draft.input is not None
    assert step_draft.output is not None


def test_scan_single_root_and_hierarchy(real_deps, mock_langfuse):
    """Đúng 1 root 'scan', child agent spans dưới root, steps lồng dưới agent span tương ứng."""
    res = scan_symbol(
        "FPT",
        price_source=real_deps.price_source,
        news_source=real_deps.news_source,
        history_store=real_deps.history_store,
        memory_store=real_deps.memory_store,
        notifier=real_deps.notifier,
        watchlist_store=real_deps.watchlist_store,
    )
    assert res.symbol == "FPT"

    # 1. Đúng 1 root trace
    assert len(mock_langfuse.roots) == 1, f"Kỳ vọng đúng 1 root trace, nhận {len(mock_langfuse.roots)}"
    root = mock_langfuse.roots[0]
    assert root.name == "scan"
    assert root.ended is True
    assert root.parent is None
    assert root.input == "FPT"
    assert isinstance(root.output, dict)
    assert root.output.get("symbol") == "FPT"

    # 2. Child agent spans dưới root
    child_names = [c.name for c in root.children]
    assert "price_agent" in child_names
    assert "news_agent" in child_names
    assert "event_classifier" in child_names

    for span in root.children:
        assert span.parent is root, f"Span {span.name} phải có parent là root trace"
        assert span.ended is True, f"Span {span.name} chưa gọi end()"
        assert span.input is not None, f"Span {span.name} thiếu input"
        assert span.output is not None, f"Span {span.name} thiếu output"

    # 3. Hierarchy nesting
    price_span = next(c for c in root.children if c.name == "price_agent")
    step_quote = next(s for s in price_span.children if s.name == "fetch_quote")
    assert step_quote.parent is price_span
    assert step_quote.input is not None
    assert step_quote.output is not None

    classifier_span = next(c for c in root.children if c.name == "event_classifier")
    step_classify = next(s for s in classifier_span.children if s.name == "classify")
    assert step_classify.parent is classifier_span
    assert step_classify.input is not None
    assert step_classify.output is not None


def test_no_duplicate_roots_per_request(real_deps, mock_langfuse):
    """Mỗi request tạo đúng 1 root trace độc lập."""
    answer_question(
        "FPT thế nào?",
        price_source=real_deps.price_source,
        news_source=real_deps.news_source,
        history_store=real_deps.history_store,
        memory_store=real_deps.memory_store,
    )
    assert len(mock_langfuse.roots) == 1

    scan_symbol(
        "VNM",
        price_source=real_deps.price_source,
        news_source=real_deps.news_source,
        history_store=real_deps.history_store,
        memory_store=real_deps.memory_store,
        notifier=real_deps.notifier,
        watchlist_store=real_deps.watchlist_store,
    )
    assert len(mock_langfuse.roots) == 2
    assert mock_langfuse.roots[0].name == "chat"
    assert mock_langfuse.roots[1].name == "scan"
