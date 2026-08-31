"""Test Buổi 7 — Monitoring (LangFuse hooks, tối thiểu).

Khi MONITORING_ENABLED=false (mặc định), trace_answer/trace_stream phải là
no-op hoàn toàn — không import package `langfuse` (chưa cài trong dev env).
Khi bật, mock `_get_langfuse` để không cần key/network thật.
"""

from __future__ import annotations

from app.monitoring import tracing


def test_trace_answer_is_noop_when_disabled(monkeypatch):
    monkeypatch.setattr(tracing.settings, "monitoring_enabled", False)

    with tracing.trace_answer("answer", "câu hỏi") as t:
        t["output"] = "trả lời"

    # Không raise, không import langfuse (nếu import sẽ ModuleNotFoundError
    # vì package chưa cài trong dev env).


def test_trace_stream_is_noop_when_disabled(monkeypatch):
    monkeypatch.setattr(tracing.settings, "monitoring_enabled", False)

    tokens = iter(["a", "b", "c"])
    result = list(tracing.trace_stream("answer_stream", "câu hỏi", tokens))
    assert result == ["a", "b", "c"]


def test_trace_answer_calls_langfuse_when_enabled(monkeypatch):
    monkeypatch.setattr(tracing.settings, "monitoring_enabled", True)

    calls = {}

    class FakeSpan:
        def update(self, **kwargs):
            calls["update"] = kwargs

        def end(self):
            calls["ended"] = True

    class FakeLangfuse:
        def start_observation(self, **kwargs):
            calls["start_observation"] = kwargs
            return FakeSpan()

        def flush(self):
            calls["flushed"] = True

    monkeypatch.setattr(tracing, "_get_langfuse", lambda: FakeLangfuse())

    with tracing.trace_answer("answer", "câu hỏi") as t:
        t["output"] = "trả lời"

    assert calls["start_observation"]["input"] == "câu hỏi"
    assert calls["update"]["output"] == "trả lời"
    assert calls["ended"] is True
    assert calls["flushed"] is True


def test_trace_stream_calls_langfuse_when_enabled(monkeypatch):
    monkeypatch.setattr(tracing.settings, "monitoring_enabled", True)

    calls = {}

    class FakeSpan:
        def end(self):
            calls["ended"] = True

    class FakeLangfuse:
        def start_observation(self, **kwargs):
            calls["start_observation"] = kwargs
            return FakeSpan()

        def flush(self):
            calls["flushed"] = True

    monkeypatch.setattr(tracing, "_get_langfuse", lambda: FakeLangfuse())

    tokens = iter(["a", "b"])
    result = list(tracing.trace_stream("answer_stream", "q", tokens))

    assert result == ["a", "b"]
    assert calls["start_observation"]["output"] == "ab"
    assert calls["ended"] is True
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


def test_trace_step_sends_usage_as_generation(monkeypatch):
    monkeypatch.setattr(tracing.settings, "monitoring_enabled", True)
    calls = {}

    class FakeGen:
        def update(self, **kwargs):
            calls["gen_update"] = kwargs

        def end(self):
            calls["gen_ended"] = True

    class FakeSpan:
        def update(self, **kwargs):
            calls["update"] = kwargs

        def end(self):
            calls["ended"] = True

        def start_observation(self, **kwargs):
            calls["generation"] = kwargs
            return FakeGen()

    class FakeLangfuse:
        def start_observation(self, **kwargs):
            return FakeSpan()

        def flush(self):
            calls["flushed"] = True

    monkeypatch.setattr(tracing, "_get_langfuse", lambda: FakeLangfuse())

    with tracing.trace_answer("answer", "câu hỏi"):
        with tracing.trace_step(
            None,
            "llm.chat_parsed",
            input=[{"role": "user", "content": "hi"}],
            model="gpt-4o-mini",
            usage={"prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 14},
        ) as t:
            t["output"] = {"symbol": "HPG"}

    gen = calls["generation"]
    assert gen["as_type"] == "generation"
    assert gen["model"] == "gpt-4o-mini"
    assert gen["usage_details"] == {"input": 10, "output": 4, "total": 14}
    assert calls["gen_update"]["output"] == {"symbol": "HPG"}
    assert calls["gen_ended"] is True
    assert calls["flushed"] is True
