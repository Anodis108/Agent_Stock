"""Test Buổi 7 — Monitoring (LangFuse hooks, tối thiểu).

Khi MONITORING_ENABLED=false (mặc định), trace_answer/trace_stream phải là
no-op hoàn toàn — không import package `langfuse` (chưa cài trong dev env).
Khi bật, mock `_get_langfuse` để không cần key/network thật.
"""

from __future__ import annotations

from contextlib import contextmanager

from app.monitoring import tracing


def test_trace_answer_is_noop_when_disabled(monkeypatch):
    monkeypatch.setattr(tracing.settings, "monitoring_enabled", False)

    with tracing.trace_answer("answer", "câu hỏi") as t:
        t["output"] = "trả lời"


def test_trace_stream_is_noop_when_disabled(monkeypatch):
    monkeypatch.setattr(tracing.settings, "monitoring_enabled", False)

    tokens = iter(["a", "b", "c"])
    result = list(tracing.trace_stream("answer_stream", "câu hỏi", tokens))
    assert result == ["a", "b", "c"]


class _FakeSpan:
    def __init__(self, calls: dict, key: str = "update"):
        self._calls = calls
        self._key = key

    def start_as_current_observation(self, **kwargs):
        self._calls.setdefault("children", []).append(kwargs)
        key = f"update_{kwargs.get('name', 'span')}"

        @contextmanager
        def _cm():
            yield _FakeSpan(self._calls, key=key)

        return _cm()

    def start_observation(self, **kwargs):
        self._calls.setdefault("orphan_children", []).append(kwargs)
        return _FakeSpan(self._calls, key="orphan_update")

    def update(self, **kwargs):
        self._calls[self._key] = kwargs

    def end(self):
        self._calls["ended"] = True


def _fake_client(calls: dict):
    class FakeLangfuse:
        def start_observation(self, **kwargs):
            calls.setdefault("roots", []).append(kwargs)
            calls["start_observation"] = kwargs
            return _FakeSpan(calls, key="update")

        def start_as_current_observation(self, **kwargs):
            calls.setdefault("client_current", []).append(kwargs)

            @contextmanager
            def _cm():
                yield _FakeSpan(calls, key="client_current_span")

            return _cm()

        def flush(self):
            calls["flushed"] = True

    return FakeLangfuse()


def test_trace_answer_calls_langfuse_when_enabled(monkeypatch):
    monkeypatch.setattr(tracing.settings, "monitoring_enabled", True)
    calls: dict = {}
    monkeypatch.setattr(tracing, "_get_langfuse", lambda: _fake_client(calls))

    with tracing.trace_answer("answer", "câu hỏi") as t:
        t["output"] = "trả lời"

    assert calls["start_observation"]["input"] == "câu hỏi"
    assert calls["update"]["output"] == "trả lời"
    assert calls["ended"] is True
    assert calls["flushed"] is True
    assert len(calls["roots"]) == 1


def test_trace_stream_calls_langfuse_when_enabled(monkeypatch):
    monkeypatch.setattr(tracing.settings, "monitoring_enabled", True)
    calls: dict = {}
    monkeypatch.setattr(tracing, "_get_langfuse", lambda: _fake_client(calls))

    tokens = iter(["a", "b"])
    result = list(tracing.trace_stream("answer_stream", "q", tokens))

    assert result == ["a", "b"]
    assert calls["start_observation"]["output"] == "ab"
    assert calls["flushed"] is True


def test_trace_step_llm_is_noop_when_disabled(monkeypatch):
    monkeypatch.setattr(tracing.settings, "monitoring_enabled", False)
    with tracing.trace_step(
        None,
        "llm.chat",
        input=[{"role": "user", "content": "hi"}],
        model="gpt-4o-mini",
        usage={"prompt_tokens": 3, "completion_tokens": 1, "total_tokens": 4},
    ) as t:
        t["output"] = "hello"


def test_trace_step_nests_under_parent_not_new_root(monkeypatch):
    """Một câu hỏi: 1 root assistant_message; db_*/synth/llm là child, không phải root."""
    monkeypatch.setattr(tracing.settings, "monitoring_enabled", True)
    calls: dict = {}
    monkeypatch.setattr(tracing, "_get_langfuse", lambda: _fake_client(calls))

    step_names = ("db_normalize", "db_read", "db_parse", "synth_compose", "llm.chat")
    with tracing.trace_answer("assistant_message", "Tại sao HPG giảm") as t:
        t["output"] = {"answer": "HPG: …"}
        for name in step_names:
            with tracing.trace_step(t.get("_span"), name, input="HPG") as step:
                step["output"] = name
            with tracing.trace_step(None, name, input="HPG") as step:
                step["output"] = name

    assert [row["name"] for row in calls["roots"]] == ["assistant_message"]
    assert "client_current" not in calls
    assert "orphan_children" not in calls
    child_names = [row["name"] for row in calls["children"]]
    assert child_names.count("db_read") == 2
    assert set(step_names) <= set(child_names)
    assert calls["update_synth_compose"]["output"] == "synth_compose"


def test_trace_step_sends_usage_as_generation(monkeypatch):
    monkeypatch.setattr(tracing.settings, "monitoring_enabled", True)
    calls: dict = {}
    monkeypatch.setattr(tracing, "_get_langfuse", lambda: _fake_client(calls))

    with tracing.trace_answer("answer", "câu hỏi"):
        with tracing.trace_step(
            None,
            "llm.chat_parsed",
            input=[{"role": "user", "content": "hi"}],
            model="gpt-4o-mini",
            usage={"prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 14},
        ) as t:
            t["output"] = {"symbol": "HPG"}

    gen = calls["children"][-1]
    assert gen["as_type"] == "generation"
    assert gen["model"] == "gpt-4o-mini"
    assert gen["usage_details"] == {"input": 10, "output": 4, "total": 14}
    assert calls["update_llm.chat_parsed"]["output"] == {"symbol": "HPG"}
    assert len(calls["roots"]) == 1


def test_hub_ask_one_root(monkeypatch):
    """run_supervisor bọc 1 `trace_answer('agent_pr_ask')` / HTTP."""
    monkeypatch.setattr(tracing.settings, "monitoring_enabled", True)
    calls: dict = {}
    monkeypatch.setattr(tracing, "_get_langfuse", lambda: _fake_client(calls))

    with tracing.trace_answer(
        "agent_pr_ask",
        "Tại sao HPG giảm",
        metadata={"thread_id": "thread-1", "user_id": "user-1"},
    ) as t:
        t["output"] = {"answer": "ok"}

    assert [row["name"] for row in calls["roots"]] == ["agent_pr_ask"]


def test_trace_step_without_parent_does_not_open_root_trace(monkeypatch):
    """Không có assistant_message → không gửi bước thành trace gốc."""
    monkeypatch.setattr(tracing.settings, "monitoring_enabled", True)
    calls: dict = {}

    class NoParent:
        def start_as_current_observation(self, **kwargs):
            calls["opened"] = kwargs

            @contextmanager
            def _cm():
                yield _FakeSpan(calls)

            return _cm()

        def start_observation(self, **kwargs):
            calls["opened_obs"] = kwargs
            return _FakeSpan(calls)

    monkeypatch.setattr(tracing, "_get_langfuse", lambda: NoParent())
    with tracing.trace_step(None, "coordinator", input="hi") as t:
        t["output"] = "x"
    assert "opened" not in calls
    assert "opened_obs" not in calls
    assert "roots" not in calls
