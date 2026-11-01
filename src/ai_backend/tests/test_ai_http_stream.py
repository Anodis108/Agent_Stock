"""AI_TRANSPORT=http: web proxy SSE, process AI phát /v1/chat/stream-sse."""

from __future__ import annotations

import io
import json
from types import SimpleNamespace
from urllib.error import URLError

from fastapi.testclient import TestClient


def _parse_sse(text: str) -> list[tuple[str, dict]]:
    events = []
    current = None
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("event:"):
            current = line.split(":", 1)[1].strip()
        elif line.startswith("data:") and current:
            events.append((current, json.loads(line.split(":", 1)[1].strip())))
            current = None
    return events


class _Body(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def close(self):
        super().close()


def test_http_transport_proxies_chat_stream(client: TestClient, monkeypatch):
    """Web không chạy answer_question. SSE từ AI được gắn session và lưu database."""
    monkeypatch.setenv("AI_TRANSPORT", "http")
    monkeypatch.setenv("AI_BASE_URL", "http://ai.test:8001")

    def _boom(*_args, **_kwargs):
        raise AssertionError("inprocess answer_question không được gọi")

    monkeypatch.setattr("web_backend.api.routers.chat._get_chat_answer_fn", lambda: _boom)

    sse = (
        'data: {"token": "xin "}\n\n'
        'data: {"answer": "xin chao", "question": "FPT?", "steps": [], "route": "qa", "complete": true}\n\n'
        "data: [DONE]\n\n"
    )
    seen: dict[str, object] = {}

    def fake_urlopen(req, timeout=None):
        seen["url"] = req.full_url
        seen["timeout"] = timeout
        seen["body"] = json.loads(req.data.decode("utf-8"))
        return _Body(sse.encode("utf-8"))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr(
        "ai_backend.infra.session.account_snapshot.load_account_snapshot",
        lambda user_id: {
            "watchlist": [
                {"symbol": "HPG", "threshold_pct": 3.0, "user_id": user_id}
            ],
            "holdings": [
                {
                    "symbol": "FPT",
                    "quantity": 10,
                    "avg_buy_price": 60.0,
                    "user_id": user_id,
                }
            ],
        },
    )

    resp = client.post("/api/v1/chat/stream", json={"question": "FPT?", "user_id": "default"})
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")
    assert seen["url"] == "http://ai.test:8001/v1/chat/stream-sse"
    assert seen["body"]["question"] == "FPT?"
    assert seen["body"]["user_id"] == "default"
    assert "watchlist" not in seen["body"]
    assert "holdings" not in seen["body"]
    assert seen["timeout"] == 300.0

    events = _parse_sse(resp.text)
    names = [name for name, _data in events]
    assert names == ["token", "complete"]
    assert events[0][1]["delta"] == "xin "
    complete = events[1][1]
    assert complete["answer"] == "xin chao"
    assert complete["session_id"]
    assert complete["message_id"]

    detail = client.get(f"/api/v1/sessions/{complete['session_id']}")
    assert detail.status_code == 200
    roles = [item["role"] for item in detail.json()["messages"]]
    assert roles == ["user", "assistant"]
    assert detail.json()["messages"][1]["content"] == "xin chao"
    assert detail.json()["messages"][1]["id"] == complete["message_id"]


def test_web_entry_forwards_ui_sse(monkeypatch, pg_schema):
    """Entry web_backend.main chỉ chuyển SSE của POST /chat sang AI."""
    from web_backend.main import app as web_app

    monkeypatch.setenv("AI_TRANSPORT", "http")
    monkeypatch.setenv("AI_BASE_URL", "http://ai.test:8001")

    def _boom(*_args, **_kwargs):
        raise AssertionError("web_backend.main không được gọi answer_question")

    monkeypatch.setattr("web_backend.api.routers.chat._get_chat_answer_fn", lambda: _boom)

    sse = (
        'data: {"token": "RSI "}\n\n'
        'data: {"token": "là chỉ báo"}\n\n'
        'data: {"answer": "RSI là chỉ báo", "question": "RSI là gì", "steps": [], "route": "concept", "source_file": "rsi-va-sma.md", "complete": true}\n\n'
        "data: [DONE]\n\n"
    )
    seen: dict[str, object] = {}

    def fake_urlopen(req, timeout=None):
        seen["url"] = req.full_url
        seen["accept"] = req.headers.get("Accept")
        seen["body"] = json.loads(req.data.decode("utf-8"))
        return _Body(sse.encode("utf-8"))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    web = TestClient(web_app)
    resp = web.post(
        "/chat",
        headers={"Accept": "text/event-stream", "X-User-ID": "user_a"},
        json={"question": "RSI là gì", "user_id": "user_a"},
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")
    assert resp.headers.get("x-accel-buffering") == "no"
    assert seen["url"] == "http://ai.test:8001/v1/chat/stream-sse"
    assert seen["accept"] == "text/event-stream"
    assert seen["body"]["question"] == "RSI là gì"
    assert seen["body"]["user_id"] == "user_a"
    assert "watchlist" not in seen["body"]
    assert "holdings" not in seen["body"]

    events = _parse_sse(resp.text)
    assert [name for name, _data in events] == ["token", "token", "complete"]
    assert events[0][1] == {"delta": "RSI "}
    assert events[1][1] == {"delta": "là chỉ báo"}
    complete = events[2][1]
    assert complete["answer"] == "RSI là chỉ báo"
    assert complete["source_file"] == "rsi-va-sma.md"
    assert complete["session_id"]
    assert complete["message_id"]

    detail = web.get(f"/api/v1/sessions/{complete['session_id']}")
    assert detail.status_code == 200
    roles = [item["role"] for item in detail.json()["messages"]]
    assert roles == ["user", "assistant"]

    fallback = web.post("/chat/stream", json={"question": "RSI là gì", "user_id": "user_a"})
    assert fallback.status_code == 200
    assert "text/event-stream" in fallback.headers.get("content-type", "")
    assert seen["url"] == "http://ai.test:8001/v1/chat/stream-sse"


def test_web_entry_sends_account_lists_only_for_live_questions(monkeypatch, pg_schema):
    """Chat HTTP chỉ gửi question + user_id; danh mục do DBAgent đọc trong AI."""
    from ai_backend.infra.storage.watchlist_store import PgWatchlistStore
    from common.domain.entities import WatchlistItem
    from web_backend.api.deps import clear_deps_cache, get_app_deps, set_app_deps
    from web_backend.api.routers import watchlist as watchlist_routes
    from web_backend.main import app as web_app

    monkeypatch.setenv("AI_TRANSPORT", "http")
    monkeypatch.setenv("AI_BASE_URL", "http://ai.test:8001")
    set_app_deps(None)
    clear_deps_cache()
    isolated = PgWatchlistStore(pg_schema)
    monkeypatch.setattr(watchlist_routes, "store", isolated)
    isolated.upsert(
        WatchlistItem(symbol="HPG", threshold_pct=4.5, user_id="user_a")
    )
    isolated.upsert(
        WatchlistItem(symbol="VNM", threshold_pct=1.0, user_id="user_b")
    )
    holdings = get_app_deps().holdings_repo
    assert holdings is not None
    holdings.create("FPT", 10, 60.0, user_id="user_a")
    holdings.create("MWG", 1, 40.0, user_id="user_b")

    seen: list[dict] = []

    def fake_urlopen(req, timeout=None):
        seen.append(json.loads(req.data.decode("utf-8")))
        sse = (
            'data: {"token": "ok"}\n\n'
            'data: {"answer": "ok", "question": "q", "steps": [], "route": "qa", "complete": true}\n\n'
            "data: [DONE]\n\n"
        )
        return _Body(sse.encode("utf-8"))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    web = TestClient(web_app)
    try:
        for question in ("Danh mục của tôi", "Giá FPT", "RSI là gì"):
            resp = web.post(
                "/chat",
                headers={"Accept": "text/event-stream", "X-User-ID": "user_a"},
                json={"question": question, "user_id": "user_a"},
            )
            assert resp.status_code == 200, question
    finally:
        set_app_deps(None)
        clear_deps_cache()

    assert len(seen) == 3
    for payload in seen:
        assert payload["user_id"] == "user_a"
        assert "watchlist" not in payload
        assert "holdings" not in payload


def test_ui_chat_post_only_forwards_ai_sse(client: TestClient, monkeypatch):
    """Trang chat gọi POST /chat. Web chỉ chuyển token từ AI, không chạy swarm."""
    monkeypatch.setenv("AI_TRANSPORT", "http")
    monkeypatch.setenv("AI_BASE_URL", "http://ai.test:8001")

    def _boom(*_args, **_kwargs):
        raise AssertionError("web không được gọi answer_question khi stream")

    monkeypatch.setattr("web_backend.api.routers.chat._get_chat_answer_fn", lambda: _boom)

    sse = (
        'data: {"token": "RSI "}\n\n'
        'data: {"token": "là chỉ báo"}\n\n'
        'data: {"answer": "RSI là chỉ báo", "question": "RSI là gì", "steps": [], "route": "concept", "source_file": "rsi-va-sma.md", "complete": true}\n\n'
        "data: [DONE]\n\n"
    )
    seen: dict[str, object] = {}

    def fake_urlopen(req, timeout=None):
        seen["url"] = req.full_url
        seen["accept"] = req.headers.get("Accept")
        return _Body(sse.encode("utf-8"))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    resp = client.post(
        "/chat",
        headers={"Accept": "text/event-stream", "X-User-ID": "user_a"},
        json={"question": "RSI là gì", "user_id": "user_a"},
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")
    assert seen["url"] == "http://ai.test:8001/v1/chat/stream-sse"
    assert seen["accept"] == "text/event-stream"

    events = _parse_sse(resp.text)
    assert [name for name, _data in events] == ["token", "token", "complete"]
    assert events[0][1] == {"delta": "RSI "}
    assert events[1][1] == {"delta": "là chỉ báo"}
    assert events[2][1]["answer"] == "RSI là chỉ báo"
    assert events[2][1]["source_file"] == "rsi-va-sma.md"
    assert events[2][1]["session_id"]


def test_http_stream_connection_error_is_sse_event(client: TestClient, monkeypatch):
    monkeypatch.setenv("AI_TRANSPORT", "http")
    monkeypatch.setattr(
        "ai_backend.infra.session.account_snapshot.load_account_snapshot",
        lambda user_id: {"watchlist": [], "holdings": []},
    )

    def fake_urlopen(req, timeout=None):
        raise URLError("connection refused")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    resp = client.post("/chat/stream", json={"question": "FPT?"})
    assert resp.status_code == 200
    events = _parse_sse(resp.text)
    assert events[0][0] == "error"
    assert "connection refused" in events[0][1]["error"]


def test_ai_service_chat_stream_endpoint(monkeypatch):
    from ai_backend.application import chat_service as chat_stream
    from ai_backend.main import app as ai_app

    def fake_events(*_args, **_kwargs):
        yield ("token", {"delta": "z"})
        yield ("complete", {"answer": "z", "question": "FPT?"})

    monkeypatch.setattr(chat_stream, "iter_swarm_events", fake_events)
    resp = TestClient(ai_app).post("/v1/chat/stream", json={"question": "FPT?"})
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")
    events = _parse_sse(resp.text)
    assert [name for name, _data in events] == ["token", "complete"]
    assert events[1][1]["answer"] == "z"


def test_iter_swarm_events_has_no_session_fields(monkeypatch):
    from ai_backend.application import chat_service as chat_stream

    def fake_answer(*_args, **kwargs):
        kwargs["event_callback"]("token", {"delta": "ab"})
        routing = SimpleNamespace(route="qa", reason="r", agents_to_call=["price"])
        rewritten = SimpleNamespace(rewritten="ab?", symbol="FPT", intent="price")
        return SimpleNamespace(
            question="ab?",
            rewritten=rewritten,
            routing=routing,
            answer="ab",
            price=None,
            news=None,
            eval_result=None,
            chart_path=None,
            source_file="rsi-va-sma.md",
            steps=[],
            error=None,
        )

    monkeypatch.setattr(chat_stream, "run_chat_graph", fake_answer)
    deps = SimpleNamespace(
        price_source=None,
        news_source=None,
        history_store=None,
        memory_store=None,
    )
    events = list(chat_stream.iter_swarm_events("ab?", deps))
    assert [name for name, _data in events] == ["token", "final_answer", "complete"]
    assert events[0][1]["delta"] == "ab"
    assert events[-1][1]["answer"] == "ab"
    assert events[-1][1]["source_file"] == "rsi-va-sma.md"
    assert "session_id" not in events[-1][1]
    assert "message_id" not in events[-1][1]


def _snapshot(user_id: str) -> dict:
    return {
        "watchlist": [{"symbol": "HPG", "threshold_pct": 4.5, "user_id": user_id}],
        "holdings": [
            {
                "symbol": "FPT",
                "quantity": 2,
                "avg_buy_price": 90.0,
                "user_id": user_id,
            }
        ],
    }


def test_http_chat_and_scan_carry_lists_only_when_needed(monkeypatch):
    monkeypatch.setenv("AI_TRANSPORT", "http")
    monkeypatch.setenv("AI_BASE_URL", "http://ai.test:8001")
    monkeypatch.setattr(
        "ai_backend.infra.session.account_snapshot.load_account_snapshot",
        _snapshot,
    )
    seen: list[tuple[str, dict]] = []

    def fake_urlopen(req, timeout=None):
        seen.append((req.full_url, json.loads(req.data.decode("utf-8"))))
        return _Body(b'{"answer": "ok", "symbol": "HPG", "route": "qa"}')

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    from common.transport import ai_chat, ai_scan

    ai_chat(question="Danh mục của tôi", user_id="user_a")
    ai_scan(symbol="HPG", user_id="user_a")
    ai_chat(question="xin chào", user_id="user_a")

    assert seen[0][0] == "http://ai.test:8001/v1/chat"
    assert "watchlist" not in seen[0][1]
    assert "holdings" not in seen[0][1]
    assert seen[1][0] == "http://ai.test:8001/v1/scan"
    assert seen[1][1]["watchlist"][0]["threshold_pct"] == 4.5
    assert seen[1][1]["holdings"][0]["symbol"] == "FPT"
    assert "watchlist" not in seen[2][1]
    assert "holdings" not in seen[2][1]


def test_concept_questions_omit_watchlist_and_holdings(monkeypatch):
    from ai_backend.infra.session.account_snapshot import (
        is_concept_question,
        question_needs_account_lists,
    )

    concept = (
        "RSI là gì",
        "SMA là gì",
        "NAV là gì",
        "ATO là gì",
        "giá trần là gì",
        "lãi lỗ chưa chốt là gì",
        "miễn trừ trách nhiệm",
        "NAV của danh mục là gì",
    )
    live = (
        "RSI của HPG",
        "Giá FPT",
        "Danh mục của tôi",
        "NAV của tôi",
        "lãi lỗ của tôi",
    )
    for question in concept:
        assert is_concept_question(question)
        assert question_needs_account_lists(question) is False
    for question in live:
        assert is_concept_question(question) is False
        assert question_needs_account_lists(question) is True

    monkeypatch.setenv("AI_TRANSPORT", "http")
    monkeypatch.setenv("AI_BASE_URL", "http://ai.test:8001")
    monkeypatch.setattr(
        "ai_backend.infra.session.account_snapshot.load_account_snapshot",
        _snapshot,
    )
    seen: list[dict] = []

    def fake_urlopen(req, timeout=None):
        seen.append(json.loads(req.data.decode("utf-8")))
        return _Body(b'{"answer": "ok"}')

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    from common.transport import ai_chat

    ai_chat(question="NAV là gì", user_id="user_a")
    ai_chat(question="giá trần là gì", user_id="user_a")
    ai_chat(question="RSI của HPG", user_id="user_a")

    for payload in seen:
        assert "watchlist" not in payload
        assert "holdings" not in payload


def test_portfolio_agent_uses_db_agent_holdings(monkeypatch):
    from ai_backend.domain.agents.chat.nodes.portfolio import run_portfolio_report

    monkeypatch.setattr(
        "ai_backend.domain.agents.scan.db_agent.read_holdings",
        lambda user_id, conn=None: [
            {
                "symbol": "FPT",
                "quantity": 10,
                "avg_buy_price": 60.0,
                "user_id": user_id,
            }
        ],
    )
    price = SimpleNamespace(
        fetch_latest_close=lambda symbol: SimpleNamespace(
            latest_close=70.0, error=None
        )
    )
    result = run_portfolio_report(
        user_id="user_a",
        intent="portfolio",
        price_source=price,
    )
    assert result.error is None
    assert result.portfolio_summary.items[0].symbol == "FPT"


def test_closing_the_chat_stream_stops_the_pipeline(monkeypatch):
    """Client đóng SSE thì worker thấy cờ hủy và không chạy tiếp."""
    import threading
    import time

    import ai_backend.domain.agents.chat.graph as answer_mod
    import common.transport.transport as transport
    from ai_backend.application import chat_service as chat_stream
    from ai_backend.domain.agents.events import StreamCancelledError, check_stream_cancelled
    from web_backend.api.routers.chat import ChatRequest, stream_chat_generator


    started = threading.Event()
    halted = threading.Event()
    kept_going = {"value": False}

    def fake_answer(*_args, **kwargs):
        kwargs["event_callback"]("node_start", {"node": "supervisor"})
        started.set()
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            try:
                check_stream_cancelled()
            except StreamCancelledError:
                halted.set()
                raise
            time.sleep(0.02)
        kept_going["value"] = True
        raise AssertionError("pipeline kept running after the client closed the stream")



    monkeypatch.setattr(answer_mod, "run_chat_graph", fake_answer)
    monkeypatch.setattr(chat_stream, "run_chat_graph", fake_answer)
    monkeypatch.setattr(transport, "_use_http", lambda: False)
    monkeypatch.setattr(
        "web_backend.api.routers.chat._prepare_stream_session",
        lambda body: ("sess-1", body.question),
    )

    deps = SimpleNamespace(
        price_source=object(),
        news_source=object(),
        history_store=object(),
        memory_store=object(),
    )
    web = stream_chat_generator(ChatRequest(question="Giá FPT"), deps)
    first = next(web)
    assert "node_start" in first
    assert started.wait(3)
    web.close()
    assert halted.wait(5)
    assert kept_going["value"] is False

    started.clear()
    halted.clear()
    ai = chat_stream.iter_swarm_events("Giá FPT", deps)
    first_ai = next(ai)
    assert first_ai[0] == "node_start"
    assert started.wait(3)
    ai.close()
    assert halted.wait(5)
    assert kept_going["value"] is False


def test_web_entry_closes_the_ai_stream_when_the_client_disconnects(monkeypatch, pg_schema):
    """Đóng POST /chat của web thì kết nối SSE tới AI bị đóng."""
    import threading

    from web_backend.main import app as web_app

    monkeypatch.setenv("AI_TRANSPORT", "http")
    monkeypatch.setenv("AI_BASE_URL", "http://ai.test:8001")

    class BlockingBody:
        def __init__(self) -> None:
            self.closed = threading.Event()
            self._lines = iter(
                [
                    b'data: {"token": "a"}',
                    b"",
                ]
            )

        def readline(self) -> bytes:
            try:
                return next(self._lines)
            except StopIteration:
                self.closed.wait(2)
                return b""

        def close(self) -> None:
            self.closed.set()

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            self.close()
            return None

    body = BlockingBody()

    def fake_urlopen(req, timeout=None):
        return body

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    web = TestClient(web_app)
    with web.stream(
        "POST",
        "/chat",
        headers={"Accept": "text/event-stream"},
        json={"question": "RSI là gì", "user_id": "user_a"},
    ) as response:
        assert response.status_code == 200
        chunk = next(response.iter_text())
        assert "token" in chunk
    assert body.closed.wait(2)
