"""Một test I/O cho mỗi worker của team chat (happy path, fake deps).

Đối xứng `test_scan_agents_io.py` (team scan).
"""

from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock

from langchain_core.messages import AIMessage

from ai_backend.domain.agents.chat import nodes
from ai_backend.domain.agents.chat.draw_agent import tools as draw_tools
from ai_backend.domain.agents.chat.draw_agent.state import DrawWorkerState
from ai_backend.domain.agents.chat.graph import CHAT_AGENTS, _RULES
from ai_backend.domain.agents.multi_agent import hierarchical as hier
from ai_backend.domain.agents.scan.state import DBAgentResult
from ai_backend.infra.charts.price_chart import ChartResult
from common.domain.ports import PriceBar


class FakeLLM:
    def __init__(self, responses: list[AIMessage]):
        self.responses = list(responses)
        self.calls: list = []

    def bind_tools(self, tools):
        return self

    async def ainvoke(self, messages):
        self.calls.append(messages)
        return self.responses.pop(0)


def tool_call(name: str, args: dict) -> AIMessage:
    return AIMessage(content="", tool_calls=[{"id": f"call_{name}", "name": name, "args": args}])


@contextmanager
def _noop_trace(*_a, **_k):
    box: dict = {}
    yield box


def test_portfolio_report_io(monkeypatch):
    monkeypatch.setattr(nodes, "trace_step", _noop_trace)
    monkeypatch.setattr(
        nodes,
        "get_runtime",
        lambda: SimpleNamespace(
            context={
                "trace_span": None,
                "price_source": SimpleNamespace(
                    fetch_latest_close=lambda symbol: SimpleNamespace(latest_close=100.0)
                ),
            }
        ),
    )
    state = {
        "user_id": "u1",
        "db_results": DBAgentResult(
            user_id="u1",
            holdings=[
                {
                    "id": "1",
                    "user_id": "u1",
                    "symbol": "FPT",
                    "quantity": 10,
                    "avg_buy_price": 90.0,
                    "purchase_date": None,
                }
            ],
            watchlist=[{"user_id": "u1", "symbol": "VNM", "threshold_pct": 3.0}],
        ),
    }

    out = nodes.portfolio_report_node(state, {})

    assert out["portfolio_report_result"]["user_id"] == "u1"
    assert out["portfolio_report_result"]["summary"]["total_nav"] > 0
    assert "FPT" in out["portfolio_report_result"]["markdown"]
    assert "VNM" in out["portfolio_report_result"]["markdown"]
    assert "NAV" in out["result"]


def test_concept_retrieval_io(monkeypatch):
    monkeypatch.setattr(
        nodes,
        "get_runtime",
        lambda: SimpleNamespace(context={"concept_client": object()}),
    )

    def fake_answer_concept(question, client=None):
        return SimpleNamespace(answer="RSI đo động lượng giá.", source_file="rsi.md")

    monkeypatch.setattr("ai_backend.infra.qdrant.answer.answer_concept", fake_answer_concept)
    monkeypatch.setattr("ai_backend.infra.storage.long_term_memory.get_qdrant_client", lambda: None)

    out = nodes.concept_retrieval_node({"question": "RSI là gì?"}, {})

    assert out["concept_answer"] == "RSI đo động lượng giá."
    assert out["source_file"] == "rsi.md"
    assert out["result"] == "RSI đo động lượng giá."


def test_answer_io(monkeypatch):
    tokens = ["Giá ", "FPT ", "tăng."]
    monkeypatch.setattr(nodes, "get_stream_writer", lambda: (lambda _t: None))
    monkeypatch.setattr(nodes, "trace_step", _noop_trace)
    monkeypatch.setattr(nodes, "trace_stream", lambda _n, _q, it: it)
    monkeypatch.setattr(nodes, "chat_stream_cached", lambda messages, params: iter(tokens))
    monkeypatch.setattr(nodes, "get_runtime", lambda: SimpleNamespace(context={"trace_span": None}))

    out = nodes.answer_node({"task": "Giá FPT?", "notes": {"price_agent": "FPT +5%"}}, {})

    assert out["answer"] == "Giá FPT tăng."
    assert out["answer_kind"] == "final_answer"


async def test_draw_agent_io(monkeypatch):
    llm = FakeLLM(
        [
            tool_call("draw_price_chart", {"symbols": ["FPT"], "chart_type": "price_history"}),
            AIMessage(content="Đã vẽ xong."),
        ]
    )
    monkeypatch.setattr(hier, "base_llm", lambda: llm)
    monkeypatch.setattr(
        draw_tools,
        "run_chart_agent",
        lambda *a, **k: ChartResult(success=True, url="/charts/fpt.png", file_path="fpt.png", symbols=["FPT"]),
    )

    class HistoryStore:
        def read_history(self, symbol, days):
            return [PriceBar(date=f"2026-01-{i + 1:02d}", close=100.0 + i) for i in range(20)]

        def upsert_bars(self, symbol, bars):
            return None

    tools, prompt, state_cls = CHAT_AGENTS["draw_agent"]
    app = hier.make_agent_graph("draw_agent", tools, f"{prompt} {_RULES}", state_cls)
    out = await app.ainvoke(
        {"task": "Vẽ biểu đồ FPT", "notes": {}, "message_worker": []},
        context={"trace_span": None, "history_store": HistoryStore(), "price_source": MagicMock()},
    )

    assert "Nhiệm vụ: Vẽ biểu đồ FPT" in llm.calls[0][1]["content"]
    assert out["chart_result"].success is True
    assert out["chart_result"].url == "/charts/fpt.png"
    assert "Đã vẽ biểu đồ" in out["result"]


async def test_scan_team_io(monkeypatch):
    fake_scan = MagicMock()
    fake_scan.ainvoke = MagicMock(
        return_value={
            "notes": {"price_agent": "FPT +5%"},
            "prices": [{"symbol": "FPT"}],
            "news": [],
        }
    )

    class Awaitable:
        def __init__(self, value):
            self.value = value

        def __await__(self):
            async def _():
                return self.value

            return _().__await__()

    fake_scan.ainvoke = lambda state, config: Awaitable(
        {"notes": {"price_agent": "FPT +5%"}, "prices": [{"symbol": "FPT"}], "news": []}
    )
    monkeypatch.setattr(nodes, "build_scan_graph", lambda: fake_scan)

    out = await nodes.scan_team_node({"task": "Giá FPT hôm nay?"}, {})

    assert out["prices"] == [{"symbol": "FPT"}]
    assert out["result"] == "[price_agent] FPT +5%"
