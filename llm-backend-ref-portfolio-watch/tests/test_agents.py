"""Kiểm thử Agent Nodes, LangGraph Workflow, Structured Output và Tracing.

Tập trung kiểm tra:
1. Các Agent Nodes: PriceAgent, NewsAgent, EventClassifier, AnswerComposer, Guardrails.
2. Biên dịch và thực thi đồ thị LangGraph (Chat Graph, Scan Graph).
3. Pydantic Schemas và cơ chế Structured Output (Retry, JSON extraction).
4. Hệ thống Tracing (agent_span, runtime telemetry).
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from backend.agents import answer_composer, synthesis_agent
from backend.agents.eval_agent.nodes import HeuristicEvalBrain
from backend.agents.eval_agent.schemas import EvalSeverityOutput
from backend.agents.event_classifier import classify_event
from backend.agents.event_classifier.schemas import ClassifierOutput
from backend.agents.news_agent import run_news_agent
from backend.agents.news_agent.schemas import NewsAgentResult, NewsReactOutput
from backend.agents.price_agent import PriceAgentResult, run_price_agent
from backend.agents.supervisor_agent.nodes import (
    HeuristicRewriteBrain,
    HeuristicSupervisorBrain,
    rewrite_question,
    route_question,
)
from backend.agents.supervisor_agent.schemas import RewriteOutput, SupervisorOutput
from backend.agents.synthesis_agent.schemas import SynthesisAlertOutput
from backend.domain.entities import EventRoute, Severity, SeverityLevel
from backend.domain.guardrails.output_checks import check_output
from backend.graph.chat import compile_chat_graph, run_chat_graph
from backend.graph.scan import compile_scan_graph
from backend.infra.llm.structured import (
    call_llm_structured,
    extract_json_str,
    parse_structured,
)
from backend.infra.market_data import CafefNewsSource, VnstockPriceSource
from backend.infra.monitoring.tracing import agent_span, trace_request, reset_client_for_tests


# ==============================================================================
# 1. Agent Execution & Nodes Tests
# ==============================================================================

def test_price_agent_real_vnstock():
    """Kiểm tra PriceAgent truy xuất dữ liệu giá từ Vnstock."""
    r = run_price_agent("FPT", VnstockPriceSource())
    if r.error:
        pytest.skip(f"vnstock không khả dụng: {r.error}")
    assert r.latest_close is not None
    assert r.change_pct is not None


def test_guardrail_blocks_buy_sell_advice():
    """Kiểm tra Guardrail chặn đứng các khuyến nghị mua/bán cổ phiếu."""
    buy = check_output("Alert", "Nhà đầu tư nên mua FPT ngay.", evidence=["change_pct=-4%"])
    sell = check_output("Alert", "Nhà đầu tư nên bán FPT ngay.", evidence=["change_pct=-4%"])
    assert buy.ok is False and sell.ok is False


def test_guardrail_shared_by_synthesis_and_answer():
    """Đảm bảo synthesis_agent và answer_composer dùng chung một hàm kiểm tra guardrail."""
    assert synthesis_agent.nodes.check_output is check_output
    assert answer_composer.nodes.check_output is check_output


def test_event_classifier_with_real_price_and_news():
    """Kiểm tra bộ phân loại sự kiện (EventClassifier) với dữ liệu giá và tin tức."""
    price = run_price_agent("FPT", VnstockPriceSource())
    if price.error:
        pytest.skip(f"vnstock không khả dụng: {price.error}")
    news = run_news_agent("FPT", CafefNewsSource(), days=7)
    routing = classify_event(price, news, threshold_pct=3.0)
    assert routing.route in (EventRoute.NORMAL, EventRoute.ABNORMAL)
    assert routing.reason.strip()


# ==============================================================================
# 2. LangGraph Workflow Tests
# ==============================================================================

def test_chat_graph_compile_and_nodes():
    """Kiểm tra đồ thị Chat Graph biên dịch thành công và chứa đầy đủ các agent node."""
    g = compile_chat_graph()
    nodes = set(g.get_graph(xray=True).nodes.keys())
    expected = {"pre_rewrite_guardrail", "guardrail_refusal", "rewrite_question", "supervisor", "workers", "answer_composer"}
    assert expected <= nodes


def test_chat_graph_execution(real_deps):
    """Kiểm tra luồng thực thi end-to-end của Chat Graph."""
    result = run_chat_graph(
        "Giá FPT hôm nay?",
        price_source=real_deps.price_source,
        news_source=real_deps.news_source,
        history_store=real_deps.history_store,
        memory_store=real_deps.memory_store,
        rewrite_brain=HeuristicRewriteBrain(),
        supervisor_brain=HeuristicSupervisorBrain(),
        turn="t1",
    )
    assert result.answer is not None
    assert len(result.steps) > 0
    step_names = [s["name"] for s in result.steps]
    assert "pre_rewrite_guardrail" in step_names or "rewrite_question" in step_names


def test_scan_graph_compiles():
    """Kiểm tra đồ thị Scan Graph biên dịch thành công."""
    g = compile_scan_graph()
    nodes = set(g.get_graph(xray=True).nodes.keys())
    assert "fetch" in nodes and "event_classifier" in nodes


# ==============================================================================
# 3. Structured Output & Pydantic Schema Validation
# ==============================================================================

def test_rewrite_schema_valid():
    """Kiểm tra schema RewriteOutput chuẩn hóa và deduplicate mã cổ phiếu."""
    out = RewriteOutput(
        rewritten="Giá FPT hôm nay?",
        symbol="fpt",
        symbols=["fpt", "VNM", "none", "FPT"],
        intent="price_lookup",
    )
    assert out.rewritten == "Giá FPT hôm nay?"
    assert out.symbol == "FPT"
    assert out.symbols == ["FPT", "VNM"]
    assert out.intent == "price_lookup"


def test_supervisor_schema_validation():
    """Kiểm tra schema SupervisorOutput chuẩn hóa danh sách sub-agents."""
    out = SupervisorOutput(
        agents_to_call=["PRICE", "NEWS", "price", "UNKNOWN"],  # type: ignore
        reason="Hỏi giá cổ phiếu",
    )
    assert out.agents_to_call == ["price", "news"]
    assert out.reason == "Hỏi giá cổ phiếu"


def test_eval_severity_schema_validation():
    """Kiểm tra schema EvalSeverityOutput với mức độ nghiêm trọng và confidence."""
    out = EvalSeverityOutput(
        level="high",
        confidence=0.85,
        reasoning="Biến động mạnh vượt ngưỡng",
    )
    assert out.level == "high"
    assert out.confidence == 0.85


def test_json_extractor_handles_markdown_codeblocks():
    """Kiểm tra hàm extract_json_str bóc tách JSON chính xác từ phản hồi có chứa ```json."""
    raw = 'Here is the response:\n```json\n{"rewritten": "FPT", "symbol": "FPT", "symbols": ["FPT"], "intent": "price_lookup"}\n```'
    extracted = extract_json_str(raw)
    parsed = parse_structured(extracted, RewriteOutput)
    assert parsed.symbol == "FPT"


def test_call_llm_structured_retry_on_parse_error():
    """Kiểm tra cơ chế retry của call_llm_structured khi LLM trả JSON sai cú pháp ở lần đầu."""
    calls = []

    def fake_chat(messages, params=None):
        calls.append(1)
        if len(calls) == 1:
            return "not a valid json"
        return json.dumps({"agents_to_call": ["price"], "reason": "tra cứu giá"})

    res = call_llm_structured([], SupervisorOutput, chat_fn=fake_chat, max_retries=2)
    assert res.agents_to_call == ["price"]
    assert len(calls) == 2


# ==============================================================================
# 4. Tracing & Agent Span Tests
# ==============================================================================

def test_agent_span_captures_input_and_output(monkeypatch):
    """Kiểm tra context manager agent_span ghi nhận đầy đủ input, output và duration."""
    from backend.shared.settings import settings
    from backend.infra.monitoring import tracing as tracing_mod

    class MockSpan:
        def __init__(self, name, input=None, metadata=None):
            self.name = name
            self.input = input
            self.metadata = metadata or {}
            self.children = []
            self.output = None
            self.ended = False

        def span(self, **kwargs):
            child = MockSpan(name=kwargs.get("name"), input=kwargs.get("input"), metadata=kwargs.get("metadata"))
            self.children.append(child)
            return child

        def start_observation(self, **kwargs):
            return self.span(**kwargs)

        def update(self, **kwargs):
            if "output" in kwargs:
                self.output = kwargs["output"]

        def end(self):
            self.ended = True

    class MockLangfuse:
        def __init__(self):
            self.roots = []

        def trace(self, **kwargs):
            root = MockSpan(name=kwargs.get("name"), input=kwargs.get("input"), metadata=kwargs.get("metadata"))
            self.roots.append(root)
            return root

        def flush(self):
            pass

    monkeypatch.setattr(settings, "monitoring_enabled", True)
    monkeypatch.setattr(settings, "langfuse_public_key", "pk-test")
    monkeypatch.setattr(settings, "langfuse_secret_key", "sk-test")
    monkeypatch.setattr(settings, "langfuse_host", "http://mock-langfuse:3000")

    mock_client = MockLangfuse()
    monkeypatch.setattr(tracing_mod, "_client", mock_client)
    reset_client_for_tests()
    monkeypatch.setattr(tracing_mod, "_client", mock_client)

    turn = "test_turn_123"
    with trace_request("chat", "FPT", metadata={"turn": turn}):
        with agent_span(turn, "test_node", input={"q": "FPT"}) as box:
            box["output"] = {"status": "ok"}

    assert len(mock_client.roots) == 1
    root = mock_client.roots[0]
    assert root.name == "chat"
    assert len(root.children) == 1
    child = root.children[0]
    assert child.name == "test_node"
    assert child.input == {"q": "FPT"}
    assert child.output == {"status": "ok"}
    assert child.ended is True
