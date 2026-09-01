"""LangFuse — 1 AGENT root ("agent_pr_ask") + AGENT con (price_agent/...) + SPAN/GENERATION cháu.

Test OTEL (InMemorySpanExporter) bắt buộc nesting thật — mock dict không đủ.
Span cha được tra theo `turn` (xem app/monitoring/tracing.py: step_parent, agent_span).
"""

from __future__ import annotations

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult
from opentelemetry.trace import format_trace_id, use_span

from app.monitoring import tracing


class ListExporter(SpanExporter):
    def __init__(self):
        self.spans: list = []

    def export(self, spans):
        self.spans.extend(spans)
        return SpanExportResult.SUCCESS

    def shutdown(self):
        return None

    def force_flush(self, timeout_millis: int = 0):
        return True


class OtelSpan:
    """Span giả Langfuse nhưng `_otel_span` là OTEL thật — test parent/trace_id."""

    def __init__(self, tracer, otel_span, name: str):
        self._tracer = tracer
        self._otel_span = otel_span
        self.name = name

    def start_observation(self, **kwargs):
        with use_span(self._otel_span, end_on_exit=False):
            child = self._tracer.start_span(str(kwargs.get("name") or "child"))
        if kwargs.get("as_type"):
            child.set_attribute("langfuse.observation.type", kwargs["as_type"])
        return OtelSpan(self._tracer, child, str(kwargs.get("name")))

    def update(self, **kwargs):
        if kwargs.get("output") is not None:
            self._otel_span.set_attribute("langfuse.observation.output", str(kwargs["output"])[:200])

    def end(self):
        if self._otel_span.is_recording():
            self._otel_span.end()


class OtelLangfuse:
    def __init__(self, tracer):
        self._tracer = tracer

    def start_observation(self, **kwargs):
        span = self._tracer.start_span(str(kwargs.get("name") or "root"))
        span.set_attribute("langfuse.observation.type", kwargs.get("as_type") or "span")
        return OtelSpan(self._tracer, span, str(kwargs.get("name")))

    def flush(self):
        return None


def _otel_client(monkeypatch):
    exporter = ListExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("langfuse-sdk")
    monkeypatch.setattr(tracing.settings, "monitoring_enabled", True)
    monkeypatch.setattr(tracing, "_get_langfuse", lambda: OtelLangfuse(tracer))
    monkeypatch.setattr(tracing, "_roots", {})
    monkeypatch.setattr(tracing, "_agents", {})
    return exporter


def _finished(exporter) -> list:
    return list(exporter.spans)


def test_disabled_is_noop(monkeypatch):
    monkeypatch.setattr(tracing.settings, "monitoring_enabled", False)
    with tracing.trace_answer("agent_pr_ask", "q") as t:
        t["output"] = "a"
    with tracing.trace_step(None, "coordinator") as t:
        t["output"] = "x"


def test_otel_exactly_one_root_and_agent_nests_steps(monkeypatch):
    """Root → coordinator (hub) + price_agent (AGENT con) → craw_fetch/llm.bind_tools lồng dưới nó."""
    exp = _otel_client(monkeypatch)
    turn = "turn-1"
    with tracing.trace_answer("agent_pr_ask", "Giá FPT?", metadata={"turn": turn}):
        with tracing.trace_step(tracing.step_parent({"turn": turn}), "guardrail_input"):
            pass
        with tracing.trace_step(tracing.step_parent({"turn": turn}), "coordinator") as c:
            c["output"] = "need_price"
        with tracing.agent_span(turn, "price_agent", input="FPT"):
            with tracing.trace_step(tracing.step_parent({"turn": turn}, "price_agent"), "craw_fetch"):
                pass
            with tracing.trace_step(
                tracing.step_parent({"turn": turn}, "price_agent"), "llm.bind_tools", model="gpt-4o-mini"
            ):
                pass

    spans = _finished(exp)
    assert len(spans) >= 5
    traces = {s.context.trace_id for s in spans}
    assert len(traces) == 1, f"spam trace_id: {len(traces)} spans={[(s.name, format_trace_id(s.context.trace_id)) for s in spans]}"

    roots = [s for s in spans if s.parent is None]
    assert len(roots) == 1, f"nhiều root: {[s.name for s in roots]}"
    assert roots[0].name == "agent_pr_ask"
    assert (roots[0].attributes or {}).get("langfuse.observation.type") == "agent"
    root_id = roots[0].context.span_id

    by_name = {s.name: s for s in spans}
    assert by_name["guardrail_input"].parent.span_id == root_id
    assert by_name["coordinator"].parent.span_id == root_id
    price_agent = by_name["price_agent"]
    assert price_agent.parent.span_id == root_id
    assert (price_agent.attributes or {}).get("langfuse.observation.type") == "agent"

    # craw_fetch / llm.bind_tools lồng dưới price_agent — KHÔNG phải trực tiếp dưới root.
    assert by_name["craw_fetch"].parent.span_id == price_agent.context.span_id
    llm = by_name["llm.bind_tools"]
    assert llm.parent.span_id == price_agent.context.span_id
    assert (llm.attributes or {}).get("langfuse.observation.type") == "generation"


def test_no_parent_exports_nothing(monkeypatch):
    exp = _otel_client(monkeypatch)
    with tracing.trace_step(None, "coordinator"):
        pass
    assert _finished(exp) == []


def test_agent_span_noop_without_root(monkeypatch):
    """agent_span() cho turn không có root đang mở → no-op, không crash."""
    exp = _otel_client(monkeypatch)
    with tracing.agent_span("no-such-turn", "price_agent") as t:
        assert t == {}
    assert _finished(exp) == []


def test_step_parent_reads_turn_from_state(monkeypatch):
    _otel_client(monkeypatch)
    turn = "turn-2"
    with tracing.trace_answer("agent_pr_ask", "q", metadata={"turn": turn}) as t:
        root_span = t["_span"]
        assert tracing.step_parent({"turn": turn}) is root_span
        assert tracing.step_parent({"turn": turn}, "price_agent") is None  # chưa mở agent_span
        assert tracing.step_parent({}) is None  # thiếu turn
        with tracing.agent_span(turn, "price_agent"):
            assert tracing.step_parent({"turn": turn}, "price_agent") is not None


def test_supervisor_state_has_no_span_field():
    from app.agent_pr.supervisor_agent.state import SupervisorState

    assert "_trace_span" not in SupervisorState.__annotations__


def test_live_langfuse_agent_nests_under_root(monkeypatch):
    """Gửi thật lên Langfuse rồi đọc API — FAIL nếu price_agent hoặc craw_fetch thành root/orphan."""
    import time

    import requests

    monkeypatch.setattr(tracing, "_client", None)
    monkeypatch.setattr(tracing, "_roots", {})
    monkeypatch.setattr(tracing, "_agents", {})
    if not tracing.settings.monitoring_enabled:
        monkeypatch.setattr(tracing.settings, "monitoring_enabled", True)
    host = (tracing.settings.langfuse_host or "").rstrip("/")
    pk = tracing.settings.langfuse_public_key
    sk = tracing.settings.langfuse_secret_key
    if not (host and pk and sk):
        raise AssertionError("thiếu LANGFUSE_HOST/KEY — không test được nesting thật")

    marker = f"nest-test-{int(time.time() * 1000)}"
    trace_id = None

    with tracing.trace_answer("agent_pr_ask", marker, metadata={"turn": marker}) as t:
        span = t.get("_span")
        trace_id = str(getattr(span, "trace_id", "") or "")
        with tracing.trace_step(tracing.step_parent({"turn": marker}), "coordinator", input=marker) as c:
            c["output"] = "need_price"
        with tracing.agent_span(marker, "price_agent", input=marker):
            with tracing.trace_step(tracing.step_parent({"turn": marker}, "price_agent"), "craw_fetch"):
                pass
            with tracing.trace_step(
                tracing.step_parent({"turn": marker}, "price_agent"),
                "llm.bind_tools",
                model="test-model",
            ):
                pass

    assert trace_id and trace_id != "-", f"không lấy được trace_id: {trace_id!r}"

    url = f"{host}/api/public/v2/observations"
    last = None
    rows = []
    for _ in range(15):
        resp = requests.get(
            url,
            params={"traceId": trace_id, "limit": 50, "fields": "core,basic,trace_context"},
            auth=(pk, sk),
            timeout=10,
        )
        last = resp
        if resp.ok:
            rows = resp.json().get("data") or []
            names = {r.get("name") for r in rows}
            if {"agent_pr_ask", "coordinator", "price_agent", "craw_fetch", "llm.bind_tools"} <= names:
                break
        time.sleep(0.4)
    assert last is not None and last.ok, f"Langfuse API {getattr(last, 'status_code', None)} {getattr(last, 'text', '')[:300]}"
    assert rows, f"không thấy observation cho trace {trace_id}"

    by_id = {r["id"]: r for r in rows}
    roots = [r for r in rows if r.get("isRootObservation") is True]
    assert len(roots) == 1, f"nhiều isRoot=True: {[(r.get('name'), r.get('type')) for r in roots]}"
    assert roots[0].get("name") == "agent_pr_ask"
    assert (roots[0].get("type") or "").upper() == "AGENT"
    assert roots[0].get("parentObservationId") in (None, "")

    by_name = {r["name"]: r for r in rows}
    coordinator = by_name["coordinator"]
    assert coordinator.get("parentObservationId") == roots[0]["id"], "coordinator phải là con trực tiếp của root"

    price_agent = by_name["price_agent"]
    assert price_agent.get("parentObservationId") == roots[0]["id"], "price_agent phải là con trực tiếp của root"
    assert (price_agent.get("type") or "").upper() == "AGENT"

    craw_fetch = by_name["craw_fetch"]
    assert craw_fetch.get("parentObservationId") == price_agent["id"], (
        "craw_fetch phải lồng dưới price_agent, không phải dưới root — đây là cây bị phẳng nếu fail"
    )
    llm = by_name["llm.bind_tools"]
    assert llm.get("parentObservationId") == price_agent["id"]
    assert (llm.get("type") or "").upper() == "GENERATION"
