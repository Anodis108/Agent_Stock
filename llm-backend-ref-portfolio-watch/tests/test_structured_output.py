"""Tests for Phase 6: Structured Output (Pydantic schemas, retry, guards, no graph crash)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from src.portfolio_watch.agents.eval_agent.nodes import HeuristicEvalBrain, LlmEvalBrain
from src.portfolio_watch.agents.eval_agent.schemas import EvalSeverityOutput
from src.portfolio_watch.agents.event_classifier.nodes import LlmEventClassifier
from src.portfolio_watch.agents.event_classifier.schemas import ClassifierOutput
from src.portfolio_watch.agents.news_agent.nodes import LlmNewsBrain
from src.portfolio_watch.agents.news_agent.schemas import NewsAgentResult, NewsReactOutput
from src.portfolio_watch.agents.price_agent import PriceAgentResult
from src.portfolio_watch.agents.supervisor_agent.nodes import (
    LlmRewriteBrain,
    LlmSupervisorBrain,
    RewrittenQuestion,
    rewrite_question,
    route_question,
)
from src.portfolio_watch.agents.supervisor_agent.schemas import (
    RewriteOutput,
    SupervisorOutput,
)
from src.portfolio_watch.agents.synthesis_agent.nodes import LlmAlertComposer
from src.portfolio_watch.agents.synthesis_agent.schemas import SynthesisAlertOutput
from src.portfolio_watch.domain.entities import EventRoute, Severity, SeverityLevel
from src.portfolio_watch.infra.llm.structured import (
    call_llm_structured,
    extract_json_str,
    parse_structured,
)
from src.portfolio_watch.shared.schemas import (
    MemoryExtractOutput,
    parse_memory_extract,
)


# ==============================================================================
# 1. Pydantic Schemas Validation Tests
# ==============================================================================

def test_rewrite_schema_valid():
    out = RewriteOutput(
        rewritten="Giá FPT hôm nay?",
        symbol="fpt",
        symbols=["fpt", "VNM", "none", "FPT"],
        intent="price_lookup",
    )
    assert out.rewritten == "Giá FPT hôm nay?"
    assert out.symbol == "FPT"
    assert out.symbols == ["FPT", "VNM"]  # Uppercased, deduplicated, 'none' removed
    assert out.intent == "price_lookup"


def test_rewrite_schema_intent_fallback():
    out = RewriteOutput(rewritten="test", intent="unknown_intent")  # type: ignore
    assert out.intent == "price_lookup"


def test_supervisor_schema_valid_and_sanitized():
    out = SupervisorOutput(
        agents_to_call=["price", "NEWS", "invalid_agent"],  # type: ignore
        reason="tra cứu giá và tin",
    )
    assert out.agents_to_call == ["price", "news"]
    assert out.reason == "tra cứu giá và tin"


def test_supervisor_schema_empty_agents_defaults_to_price():
    out = SupervisorOutput(agents_to_call=[])
    assert out.agents_to_call == ["price"]


def test_classifier_schema_to_routing_decision():
    abnormal = ClassifierOutput(route="bất thường", reason="giảm sâu 7%").to_routing_decision()
    assert abnormal.route == EventRoute.ABNORMAL
    assert "giảm sâu" in abnormal.reason

    normal = ClassifierOutput(route="bình thường", reason="dao động nhỏ").to_routing_decision()
    assert normal.route == EventRoute.NORMAL

    # Unrecognized route guards to NORMAL
    unknown = ClassifierOutput(route="la_lung", reason="không rõ").to_routing_decision()
    assert unknown.route == EventRoute.NORMAL


def test_eval_severity_schema_to_severity():
    out = EvalSeverityOutput(
        needs_history=False,
        level="high",
        confidence=1.5,  # Clamped to 1.0
        reasoning="Biến động lớn vượt ngưỡng",
        evidence=["change_pct=-7.00%"],
        proposed_threshold_pct=3.5,
        proposed_related_symbols=["hpg", "HPG", " "],
    )
    sev = out.to_severity()
    assert sev.level == SeverityLevel.HIGH
    assert sev.confidence == 1.0
    assert sev.reasoning == "Biến động lớn vượt ngưỡng"
    assert sev.evidence == ["change_pct=-7.00%"]
    assert sev.proposed_threshold_pct == 3.5
    assert sev.proposed_related_symbols == ["HPG"]


def test_synthesis_alert_schema():
    out = SynthesisAlertOutput(
        title="  Cảnh báo FPT giảm sàn  ",
        body="  Nội dung cảnh báo...  ",
    )
    assert out.title == "Cảnh báo FPT giảm sàn"
    assert out.body == "Nội dung cảnh báo..."


def test_news_react_schema():
    search = NewsReactOutput(kind="search", query=" FPT kết quả kinh doanh ")
    assert search.kind == "search"
    assert search.query == "FPT kết quả kinh doanh"

    finish = NewsReactOutput(kind="finish", query=None)
    assert finish.kind == "finish"
    assert finish.query is None


def test_memory_extract_schema():
    raw = {
        "symbols": ["fpt", "mwg"],
        "preferences": {"tone": "ngắn gọn"},
        "summary": "Người dùng quan tâm giá FPT và MWG",
        "topics": ["công nghệ", "bán lẻ"],
    }
    out = parse_memory_extract(raw)
    assert isinstance(out, MemoryExtractOutput)
    assert out.symbols == ["FPT", "MWG"]
    assert out.preferences == {"tone": "ngắn gọn"}
    assert "FPT" in out.summary

    # Invalid input fallback guard
    bad = parse_memory_extract("not a json at all {{{")
    assert isinstance(bad, MemoryExtractOutput)
    assert bad.symbols == []


# ==============================================================================
# 2. Structured Parsing Helper Tests (parse_structured & extract_json_str)
# ==============================================================================

def test_extract_json_str_raw_and_markdown():
    raw = '{"rewritten": "Giá FPT?", "symbol": "FPT"}'
    assert extract_json_str(raw) == raw

    fenced = '```json\n{"rewritten": "Giá FPT?", "symbol": "FPT"}\n```'
    assert extract_json_str(fenced) == raw

    surrounded = 'Dưới đây là JSON:\n{"rewritten": "Giá FPT?", "symbol": "FPT"}\nCảm ơn.'
    assert extract_json_str(surrounded) == raw


def test_parse_structured_from_dict_and_str():
    d = {"rewritten": "FPT?", "symbol": "FPT", "symbols": ["FPT"], "intent": "price_lookup"}
    res1 = parse_structured(d, RewriteOutput)
    assert isinstance(res1, RewriteOutput)
    assert res1.symbol == "FPT"

    s = json.dumps(d)
    res2 = parse_structured(s, RewriteOutput)
    assert isinstance(res2, RewriteOutput)
    assert res2.symbol == "FPT"


def test_call_llm_structured_retry_on_bad_json():
    attempts = 0

    def flaky_chat(messages, params):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return "This is not json at all"
        return '{"agents_to_call": ["price"], "reason": "tra cứu giá"}'

    res = call_llm_structured([], SupervisorOutput, chat_fn=flaky_chat, max_retries=1)
    assert isinstance(res, SupervisorOutput)
    assert attempts == 2
    assert res.agents_to_call == ["price"]


# ==============================================================================
# 3. Path Rewrite Tests (LlmRewriteBrain)
# ==============================================================================

def test_rewrite_path_success_with_chat_parsed():
    """Rewrite dùng structured output thành công qua mock chat_parsed_fn."""
    mock_parsed = RewriteOutput(
        rewritten="[FPT] Giá FPT hôm nay?",
        symbol="FPT",
        symbols=["FPT"],
        intent="price_lookup",
    )
    brain = LlmRewriteBrain(chat_parsed_fn=lambda msgs, schema, params: mock_parsed)
    res = brain.rewrite("Giá FPT?", [])

    assert isinstance(res, RewrittenQuestion)
    assert res.symbol == "FPT"
    assert res.symbols == ["FPT"]
    assert res.intent == "price_lookup"
    assert "FPT" in res.rewritten


def test_rewrite_path_success_with_chat_fn_json():
    """Rewrite dùng JSON string từ chat_fn được validate qua schema."""
    fake_json = json.dumps({
        "rewritten": "[HPG+VNM] So sánh HPG và VNM",
        "symbol": "HPG",
        "symbols": ["HPG", "VNM"],
        "intent": "explain",
    })
    brain = LlmRewriteBrain(chat_fn=lambda msgs, params: fake_json)
    res = brain.rewrite("So sánh HPG và VNM?", [])

    assert isinstance(res, RewrittenQuestion)
    assert res.symbol == "HPG"
    assert "VNM" in res.symbols
    assert res.intent == "explain"


def test_rewrite_path_schema_error_retries_and_guards_without_crash():
    """Schema lỗi (JSON hỏng hoặc sai type) -> retry/guard bắt lỗi, không crash graph."""
    calls = 0

    def bad_chat(msgs, params):
        nonlocal calls
        calls += 1
        return "Not valid JSON! Error 500."

    brain = LlmRewriteBrain(chat_fn=bad_chat)
    # Không được raise exception
    res = rewrite_question("Giá FPT hôm nay ra sao?", [], brain=brain, turn="t1")

    assert calls >= 2  # Đã thử retry
    assert isinstance(res, RewrittenQuestion)
    assert res.symbol == "FPT"  # Guard trích xuất symbol an toàn từ text
    assert res.original == "Giá FPT hôm nay ra sao?"


# ==============================================================================
# 4. Path Supervisor Tests (LlmSupervisorBrain)
# ==============================================================================

def test_supervisor_path_success_with_chat_parsed():
    """Supervisor routing dùng structured output thành công qua mock chat_parsed_fn."""
    mock_parsed = SupervisorOutput(
        agents_to_call=["price", "news", "eval"],
        reason="Câu hỏi so sánh cần phân tích toàn diện",
    )
    brain = LlmSupervisorBrain(chat_parsed_fn=lambda msgs, schema, params: mock_parsed)
    rw = RewrittenQuestion(
        original="So sánh FPT",
        rewritten="[FPT] So sánh FPT",
        symbol="FPT",
        intent="explain",
        symbols=["FPT"],
    )
    decision = brain.route(rw)

    assert decision.agents_to_call == ["price", "news", "eval"]
    assert "toàn diện" in decision.reason


def test_supervisor_path_success_with_chat_fn_json():
    """Supervisor routing qua chat_fn trả JSON hợp lệ."""
    fake_json = json.dumps({
        "agents_to_call": ["price"],
        "reason": "Chỉ hỏi giá hiện tại",
    })
    brain = LlmSupervisorBrain(chat_fn=lambda msgs, params: fake_json)
    rw = RewrittenQuestion(
        original="Giá FPT",
        rewritten="[FPT] Giá FPT",
        symbol="FPT",
        intent="price_lookup",
        symbols=["FPT"],
    )
    decision = brain.route(rw)

    assert decision.agents_to_call == ["price"]
    assert decision.reason == "Chỉ hỏi giá hiện tại"


def test_supervisor_path_schema_error_retries_and_guards_without_crash():
    """Supervisor schema lỗi -> retry/guard bắt lỗi, fallback an toàn, không crash graph."""
    calls = 0

    def broken_chat(msgs, params):
        nonlocal calls
        calls += 1
        return "{broken json: true"

    brain = LlmSupervisorBrain(chat_fn=broken_chat)
    rw = RewrittenQuestion(
        original="FPT có tin gì mới?",
        rewritten="[FPT] FPT có tin gì mới?",
        symbol="FPT",
        intent="news_lookup",
        symbols=["FPT"],
    )
    # Outer route_question gọi brain.route
    decision = route_question(rw, brain=brain, turn="t2")

    assert calls >= 2  # Đã thử retry
    assert "price" in decision.agents_to_call
    assert "news" in decision.agents_to_call
    assert "fallback" in decision.reason.lower()


# ==============================================================================
# 5. Other Agents Structured Output Tests (Classifier, Eval, Synthesis, News)
# ==============================================================================

def test_classifier_path_structured_and_fallback():
    p = PriceAgentResult(symbol="FPT", latest_close=100.0, prev_close=99.0, change_pct=1.0)
    n = NewsAgentResult(symbol="FPT", items=[])

    # Success path
    fake_ok = json.dumps({"route": "bình thường", "reason": "biến động nhẹ"})
    c_brain_ok = LlmEventClassifier(chat_fn=lambda m, p: fake_ok)
    res_ok = c_brain_ok.classify(p, n, threshold_pct=3.0)
    assert res_ok.route == EventRoute.NORMAL

    # Error path -> fallback to Heuristic without crash
    c_brain_err = LlmEventClassifier(chat_fn=lambda m, p: "error")
    res_err = c_brain_err.classify(p, n, threshold_pct=3.0)
    assert res_err.route == EventRoute.NORMAL


def test_eval_agent_path_structured_and_fallback():
    p = PriceAgentResult(symbol="FPT", latest_close=100.0, prev_close=92.0, change_pct=8.0)
    n = NewsAgentResult(symbol="FPT", items=[])

    # Success path
    fake_eval = json.dumps({
        "needs_history": False,
        "level": "high",
        "confidence": 0.9,
        "reasoning": "Biến động mạnh 8%",
        "evidence": ["change_pct=8.00%"],
    })
    brain_ok = LlmEvalBrain(chat_fn=lambda m, pr: fake_eval)
    sev = brain_ok.build_severity(p, n, [])
    assert sev.level == SeverityLevel.HIGH
    assert sev.confidence == 0.9

    # Error path -> fallback to heuristic
    brain_err = LlmEvalBrain(chat_fn=lambda m, pr: "broken json")
    sev_err = brain_err.build_severity(p, n, [])
    assert sev_err.level == SeverityLevel.HIGH  # Heuristic detects |change| >= 7 -> HIGH


def test_synthesis_alert_path_structured_and_fallback():
    sev = Severity(
        level=SeverityLevel.HIGH,
        confidence=0.9,
        reasoning="Biến động lớn",
        evidence=["change_pct=8.00%"],
    )

    # Success path
    fake_alert = json.dumps({
        "title": "Cảnh báo FPT biến động mạnh",
        "body": "FPT tăng 8%. Đây là thông tin tham khảo, không phải lời khuyên đầu tư.",
    })
    comp_ok = LlmAlertComposer(chat_fn=lambda m, pr: fake_alert)
    title, body = comp_ok.compose("FPT", sev, {}, model="gpt-4o-mini", attempt=0, previous_violations=[])
    assert "FPT" in title
    assert "8%" in body

    # Error path -> fallback to heuristic
    comp_err = LlmAlertComposer(chat_fn=lambda m, pr: "corrupted json")
    t_err, b_err = comp_err.compose("FPT", sev, {}, model="gpt-4o-mini", attempt=0, previous_violations=[])
    assert "FPT" in t_err
    assert "HIGH" in t_err or "nghiêm trọng" in t_err.lower() or "Cảnh báo" in t_err


def test_news_agent_path_structured_and_fallback():
    fake_news = json.dumps({"kind": "search", "query": "FPT lợi nhuận quý 3"})
    brain_ok = LlmNewsBrain(chat_fn=lambda m, pr: fake_news)
    action = brain_ok.decide("FPT", [], step=0)
    assert action.kind == "search"
    assert action.query == "FPT lợi nhuận quý 3"

    # Error path -> finish safely
    brain_err = LlmNewsBrain(chat_fn=lambda m, pr: "invalid json")
    act_err = brain_err.decide("FPT", [], step=0)
    assert act_err.kind == "finish"


# ==============================================================================
# 6. End-to-End Chat Graph with Structured Output & Schema Fail Guard
# ==============================================================================

class _FakePriceSource:
    def fetch_latest_close(self, symbol: str):
        from src.portfolio_watch.domain.ports import PriceQuote
        return PriceQuote(symbol=symbol, latest_close=120.0, prev_close=118.0)


class _FakeNewsSource:
    def fetch_news(self, symbol: str, query=None, *, days=None):
        from src.portfolio_watch.domain.ports import NewsItem
        return [NewsItem(title=f"Tin {symbol}", snippet="Kinh doanh ổn định", symbol=symbol)]


class _FakeMemoryStore:
    def __init__(self):
        self.conv = []

    def read_preferences(self, user_id="default"):
        return {}

    def write_preferences(self, user_id, prefs):
        pass

    def append_conversation(self, user_id, role, content, *, created_at=None):
        self.conv.append({"role": role, "content": content, "created_at": created_at})

    def list_conversation(self, user_id, limit=20, *, ttl_minutes=None):
        n = max(int(limit or 20), 1)
        return self.conv[-n:]

    def append_alert_event(self, user_id, event):
        pass

    def list_alert_events(self, user_id, limit=20):
        return []

    def record_rejection(self, user_id, *, gate, reason, context=None):
        pass


class _FakeHistoryStore:
    def read_history(self, symbol, days=30):
        return []


def test_chat_graph_with_structured_output_success():
    """Chat graph chạy qua LLM rewrite + supervisor structured output thành công."""
    from src.portfolio_watch.graph.chat import run_chat_graph

    rw_parsed = RewriteOutput(
        rewritten="[FPT] Giá FPT hôm nay?",
        symbol="FPT",
        symbols=["FPT"],
        intent="price_lookup",
    )
    sup_parsed = SupervisorOutput(
        agents_to_call=["price"],
        reason="tra cứu giá FPT",
    )

    rw_brain = LlmRewriteBrain(chat_parsed_fn=lambda msgs, schema, p: rw_parsed)
    sup_brain = LlmSupervisorBrain(chat_parsed_fn=lambda msgs, schema, p: sup_parsed)

    res = run_chat_graph(
        "Giá FPT hôm nay?",
        price_source=_FakePriceSource(),
        news_source=_FakeNewsSource(),
        history_store=_FakeHistoryStore(),
        memory_store=_FakeMemoryStore(),
        rewrite_brain=rw_brain,
        supervisor_brain=sup_brain,
        turn="t_graph_ok",
    )
    assert res.answer
    assert res.rewritten.symbol == "FPT"
    assert res.routing.agents_to_call == ["price"]
    assert any(s["name"] == "rewrite_question" for s in res.steps)


def test_chat_graph_schema_error_does_not_crash():
    """Khi cả rewrite và supervisor trả schema hỏng -> inner guard fallback, graph không crash."""
    from src.portfolio_watch.graph.chat import run_chat_graph

    # Cả hai đều trả text hỏng gây schema error
    rw_brain = LlmRewriteBrain(chat_fn=lambda msgs, p: "corrupted json error")
    sup_brain = LlmSupervisorBrain(chat_fn=lambda msgs, p: "another corrupted json")

    res = run_chat_graph(
        "Giá FPT hôm nay?",
        price_source=_FakePriceSource(),
        news_source=_FakeNewsSource(),
        history_store=_FakeHistoryStore(),
        memory_store=_FakeMemoryStore(),
        rewrite_brain=rw_brain,
        supervisor_brain=sup_brain,
        turn="t_graph_err",
    )
    # Graph hoàn thành an toàn đến END, sinh ra câu trả lời hợp lệ
    assert res.answer
    assert res.rewritten.symbol == "FPT"
    assert "price" in res.routing.agents_to_call



def test_diagram_plan_schema():
    from src.portfolio_watch.shared.schemas import DiagramPlanOutput
    out = DiagramPlanOutput(
        title="Luồng xử lý FPT",
        nodes=["nodeA", "nodeB"],
        edges=[{"from": "nodeA", "to": "nodeB"}],
        mermaid="graph TD\nnodeA --> nodeB",
        format="mermaid"
    )
    assert out.title == "Luồng xử lý FPT"
    assert out.nodes == ["nodeA", "nodeB"]
    
    js = out.to_graph_json()
    assert js["title"] == "Luồng xử lý FPT"
    assert js["nodes"] == ["nodeA", "nodeB"]
    assert js["edges"] == [{"from": "nodeA", "to": "nodeB"}]
