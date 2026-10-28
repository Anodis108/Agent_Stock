"""Test in / out từng agent của team scan (price / news / db / eval subgraph + event_classifier / synthesis node).

LLM giả lập ngay trong file test: trả lần lượt AIMessage có tool_call rồi câu tóm tắt cuối.
Deps (price_source, news_source, history_store, watchlist_store) cũng là fake truyền qua `context`.
"""

from __future__ import annotations

from types import SimpleNamespace

from langchain_core.messages import AIMessage, HumanMessage

from ai_backend.domain.agents.scan import nodes
from ai_backend.domain.agents.scan.db_agent import graph as db_graph
from ai_backend.domain.agents.scan.db_agent import tools as db_tools
from ai_backend.domain.agents.scan.eval_agent import graph as eval_graph
from ai_backend.domain.agents.scan.news_agent import graph as news_graph
from ai_backend.domain.agents.scan.price_agent import graph as price_graph
from ai_backend.domain.agents.scan.state import EvalAgentResult, NewsAgentResult, PriceAgentResult
from common.domain.entities import AlertStatus, EventRoute, Severity, SeverityLevel
from common.domain.ports import NewsItem, PriceBar
from common.transport.schemas import ClassifierOutput, SynthesisAlertOutput


class FakeLLM:
    """Trả lần lượt các AIMessage đã định sẵn; ghi lại messages đầu vào."""

    def __init__(self, responses: list[AIMessage]):
        self.responses = list(responses)
        self.calls: list = []

    async def ainvoke(self, messages):
        self.calls.append(messages)
        return self.responses.pop(0)


def tool_call(name: str, args: dict) -> AIMessage:
    return AIMessage(content="", tool_calls=[{"id": f"call_{name}", "name": name, "args": args}])


# ── price_agent ──────────────────────────────────────────────────────────────


async def test_price_agent_io(monkeypatch):
    llm = FakeLLM([tool_call("get_stock_price", {"symbol": "fpt"}), AIMessage(content="FPT tăng 5%.")])
    monkeypatch.setattr(price_graph, "_worker_llm", lambda: llm)

    class PriceSource:
        def fetch_latest_close(self, symbol):
            return SimpleNamespace(latest_close=105.0, prev_close=100.0, error=None)

    out = await price_graph.build_price_agent().ainvoke(
        {"task": "Lấy giá FPT", "notes": {}}, context={"trace_span": None, "price_source": PriceSource()}
    )

    assert "Nhiệm vụ: Lấy giá FPT" in llm.calls[0][1]["content"]
    assert out["prices"] == [PriceAgentResult(symbol="FPT", latest_close=105.0, prev_close=100.0, change_pct=5.0)]
    assert out["result"] == "FPT: đóng cửa 105.0, phiên trước 100.0, thay đổi 5.00%"


async def test_price_agent_source_error(monkeypatch):
    llm = FakeLLM([tool_call("get_stock_price", {"symbol": "XYZ"}), AIMessage(content="Lỗi.")])
    monkeypatch.setattr(price_graph, "_worker_llm", lambda: llm)

    class PriceSource:
        def fetch_latest_close(self, symbol):
            raise RuntimeError("mất mạng")

    out = await price_graph.build_price_agent().ainvoke(
        {"task": "Lấy giá XYZ", "notes": {}}, context={"trace_span": None, "price_source": PriceSource()}
    )

    assert out["prices"][0].latest_close is None
    assert "mất mạng" in out["prices"][0].error
    assert out["result"].startswith("XYZ: lỗi")


async def test_price_agent_no_tool_call(monkeypatch):
    """LLM không gọi tool → result = câu trả lời LLM, không có prices."""
    monkeypatch.setattr(price_graph, "_worker_llm", lambda: FakeLLM([AIMessage(content="Đã có giá trong ghi chú.")]))

    out = await price_graph.build_price_agent().ainvoke({"task": "Lấy giá FPT", "notes": {"news_agent": "x"}}, context={"trace_span": None})

    assert out["result"] == "Đã có giá trong ghi chú."
    assert not out.get("prices")


# ── news_agent ───────────────────────────────────────────────────────────────


async def test_news_agent_io(monkeypatch):
    llm = FakeLLM([tool_call("get_stock_news", {"symbol": "fpt", "query": "lợi nhuận"}), AIMessage(content="2 tin.")])
    monkeypatch.setattr(news_graph, "_worker_llm", lambda: llm)
    seen = {}

    class NewsSource:
        def fetch_news(self, symbol, query, days):
            seen.update(symbol=symbol, query=query, days=days)
            return [NewsItem(title="FPT lãi kỷ lục"), NewsItem(title="FPT ký hợp đồng")]

    out = await news_graph.build_news_agent().ainvoke(
        {"task": "Tin FPT", "notes": {}}, context={"trace_span": None, "news_source": NewsSource(), "news_days": 3}
    )

    assert seen == {"symbol": "FPT", "query": "lợi nhuận", "days": 3}
    assert out["news"] == [NewsAgentResult(symbol="FPT", items=[NewsItem(title="FPT lãi kỷ lục"), NewsItem(title="FPT ký hợp đồng")])]
    assert out["result"] == "FPT: 2 tin — FPT lãi kỷ lục; FPT ký hợp đồng"


async def test_news_agent_source_error(monkeypatch):
    llm = FakeLLM([tool_call("get_stock_news", {"symbol": "FPT"}), AIMessage(content="Lỗi.")])
    monkeypatch.setattr(news_graph, "_worker_llm", lambda: llm)

    class NewsSource:
        def fetch_news(self, symbol, query, days):
            raise RuntimeError("CafeF down")

    out = await news_graph.build_news_agent().ainvoke({"task": "Tin FPT", "notes": {}}, context={"trace_span": None, "news_source": NewsSource(), "news_days": 7})

    assert out["news"][0].items == []
    assert "CafeF down" in out["news"][0].error
    assert out["result"].startswith("FPT: lỗi")


# ── db_agent ─────────────────────────────────────────────────────────────────


async def test_db_agent_io(monkeypatch):
    llm = FakeLLM([tool_call("read_user_portfolio", {}), AIMessage(content="1 mã nắm giữ.")])
    monkeypatch.setattr(db_graph, "_worker_llm", lambda: llm)
    holdings = [{"id": "1", "user_id": "u1", "symbol": "FPT", "quantity": 100.0, "avg_buy_price": 90.0, "purchase_date": None}]
    monkeypatch.setattr(db_tools, "read_holdings", lambda user_id: holdings if user_id == "u1" else [])

    class WatchlistStore:
        def list_items(self, user_id):
            return [SimpleNamespace(user_id=user_id, symbol="VNM", threshold_pct=4.0)]

    out = await db_graph.build_db_agent().ainvoke(
        {"task": "Đọc danh mục", "notes": {}, "user_id": "u1"}, context={"watchlist_store": WatchlistStore()}
    )

    db = out["db_results"]
    assert db.user_id == "u1"
    assert db.holdings == holdings
    assert db.watchlist == [{"user_id": "u1", "symbol": "VNM", "threshold_pct": 4.0}]
    assert db.error is None
    assert out["result"].startswith("1 mã nắm giữ, 1 mã watchlist:")


async def test_db_agent_read_error(monkeypatch):
    llm = FakeLLM([tool_call("read_user_portfolio", {}), AIMessage(content="Lỗi.")])
    monkeypatch.setattr(db_graph, "_worker_llm", lambda: llm)

    def boom(user_id):
        raise RuntimeError("DB down")

    monkeypatch.setattr(db_tools, "read_holdings", boom)

    out = await db_graph.build_db_agent().ainvoke({"task": "Đọc danh mục", "notes": {}, "user_id": "u1"}, context={})

    assert out["db_results"].error == "lỗi đọc DB: DB down"
    assert out["result"] == "lỗi đọc DB: DB down"


# ── eval_agent ───────────────────────────────────────────────────────────────


async def test_eval_agent_io(monkeypatch):
    llm = FakeLLM([
        tool_call("get_technical_indicators", {"symbol": "FPT", "days": 30}),
        tool_call("submit_severity", {
            "symbol": "FPT", "level": "high", "confidence": 0.8,
            "reasoning": "tăng mạnh kèm tin", "evidence": ["FPT.change_pct=7.20%"],
        }),
        AIMessage(content="Mức high."),
    ])
    monkeypatch.setattr(eval_graph, "_worker_llm", lambda: llm)
    seen = {}

    class HistoryStore:
        def read_history(self, symbol, days):
            seen.update(symbol=symbol, days=days)
            return [PriceBar(date=f"2026-01-{i + 1:02d}", close=100.0 + i) for i in range(30)]

    out = await eval_graph.build_eval_agent().ainvoke(
        {"task": "Đánh giá FPT", "notes": {"price_agent": "FPT +7.2%"}}, context={"trace_span": None, "history_store": HistoryStore()}
    )

    assert seen == {"symbol": "FPT", "days": 30}
    assert "[price_agent] FPT +7.2%" in llm.calls[0][1]["content"]
    sev = out["eval_result"].severity
    assert (sev.level, sev.confidence, sev.evidence) == (SeverityLevel.HIGH, 0.8, ["FPT.change_pct=7.20%"])
    assert "FPT: 30 phiên" in out["result"]
    assert "FPT: đã ghi mức high" in out["result"]
    assert not out.get("messages")  # không đề xuất HITL


async def test_eval_agent_propose_watchlist_update(monkeypatch):
    llm = FakeLLM([
        tool_call("propose_watchlist_update", {"symbol": "fpt", "threshold_pct": 5.0, "related_symbols": ["CMG"]}),
        AIMessage(content="Đã đề xuất."),
    ])
    monkeypatch.setattr(eval_graph, "_worker_llm", lambda: llm)

    out = await eval_graph.build_eval_agent().ainvoke({"task": "Quét cảnh báo FPT", "notes": {}, "user_id": "u1"})

    proposal = out["messages"][-1].tool_calls[0]
    assert proposal["name"] == "update_watchlist"
    assert proposal["args"] == {"user_id": "u1", "symbol": "FPT", "threshold_pct": 5.0, "related_symbols": ["CMG"]}
    assert out["result"] == "đã tạo đề xuất cập nhật watchlist (chờ duyệt)"


async def test_eval_agent_no_history(monkeypatch):
    llm = FakeLLM([tool_call("get_technical_indicators", {"symbol": "FPT"}), AIMessage(content="Thiếu dữ liệu.")])
    monkeypatch.setattr(eval_graph, "_worker_llm", lambda: llm)

    class HistoryStore:
        def read_history(self, symbol, days):
            return []

    out = await eval_graph.build_eval_agent().ainvoke({"task": "Đánh giá FPT", "notes": {}}, context={"trace_span": None, "history_store": HistoryStore()})

    assert out["result"] == "FPT: chưa có lịch sử giá"
    assert not out.get("eval_result")


# ── event_classifier_node ────────────────────────────────────────────────────


async def test_event_classifier_node_io(monkeypatch):
    seen = {}

    def fake_llm(messages, schema, params):
        seen["prompt"] = messages[0]["content"]
        return ClassifierOutput(route="bất thường", reason="tăng 7% vượt ngưỡng")

    monkeypatch.setattr(nodes, "call_llm_structured", fake_llm)
    monkeypatch.setattr(nodes, "get_runtime", lambda: SimpleNamespace(context={"trace_span": None}))
    state = {
        "symbols": ["FPT"],
        "threshold_pct": 3.0,
        "prices": [
            PriceAgentResult(symbol="VNM", latest_close=60.0, prev_close=60.0, change_pct=0.0),
            PriceAgentResult(symbol="FPT", latest_close=107.2, prev_close=100.0, change_pct=7.2),
        ],
        "news": [NewsAgentResult(symbol="FPT", items=[NewsItem(title="FPT lãi kỷ lục")])],
    }

    out = await nodes.event_classifier_node(state, {})

    assert "FPT" in seen["prompt"] and "7.2" in seen["prompt"] and "FPT lãi kỷ lục" in seen["prompt"]
    assert out["event_routing"].route == EventRoute.ABNORMAL
    assert out["result"] == f"{EventRoute.ABNORMAL.value} — tăng 7% vượt ngưỡng"


# ── synthesis_node ───────────────────────────────────────────────────────────


async def test_synthesis_node_io(monkeypatch):
    monkeypatch.setattr(
        nodes, "call_llm_structured",
        lambda messages, schema, params: SynthesisAlertOutput(title="FPT biến động mạnh", body="FPT tăng 7.2% kèm tin lãi kỷ lục."),
    )
    sent = []

    class Notifier:
        def send(self, alert):
            sent.append(alert)
            alert.status = AlertStatus.SENT

    monkeypatch.setattr(nodes, "get_runtime", lambda: SimpleNamespace(context={"trace_span": None, "notifier": Notifier()}))
    severity = Severity(level=SeverityLevel.HIGH, confidence=0.8, reasoning="tăng mạnh", evidence=["rsi=72"])
    state = {"symbols": ["FPT"], "user_id": "u1", "eval_result": EvalAgentResult(severity=severity)}

    out = await nodes.synthesis_node(state, {})

    alert = out["alert"]
    assert (alert.symbol, alert.title, alert.status) == ("FPT", "FPT biến động mạnh", AlertStatus.SENT)
    assert alert.severity == severity
    assert alert.metadata == {"user_id": "u1"}
    assert sent == [alert]  # gửi ngay, không chờ duyệt
    assert "messages" not in out
    assert out["result"] == "đã gửi cảnh báo 'FPT biến động mạnh'"


# ── resolve_scan_threshold ───────────────────────────────────────────────────


def test_resolve_scan_threshold_from_watchlist():
    class WatchlistStore:
        def get(self, user_id, symbol):
            return SimpleNamespace(threshold_pct=4.5)

    assert nodes.resolve_scan_threshold("FPT", "u1", {"threshold_pct": None, "watchlist_store": WatchlistStore()}) == 4.5
    assert nodes.resolve_scan_threshold("FPT", "u1", {"threshold_pct": 2.0, "watchlist_store": None}) == 2.0
