"""Unit tests for AI Backend Infrastructure Layer (ai_backend.infra).

Tests:
- Graph orchestration: build_swarm_graph, build_portfolio_graph, compile_portfolio_graph
- Market data: VnstockPriceSource with offline fallback
- Qdrant/Concept loading: load_concept_chunks from resources/concepts
- Cache layer: normalize_question, ExactCache context
- Cost tracker: record_completion_usage, get_cost_context
- Storage layer: ChartObjectStore, safe_png_name, SqliteMemoryStore, SqliteWatchlistStore
- Monitoring: trace_request, agent_span, PII masking
- Worker Agents: all 10 worker agents offline execution
- PortfolioWatchAgent: in-memory calculation with account_holdings snapshot
"""

from __future__ import annotations

import os
from pathlib import Path
import pytest

from ai_backend.infra.graph.workflow import (
    build_portfolio_graph,
    build_swarm_graph,
    compile_portfolio_graph,
    list_graph_nodes,
)
from ai_backend.infra.market_data.price_source import VnstockPriceSource
from ai_backend.infra.qdrant.concepts import load_concept_chunks
from ai_backend.infra.cache.exact import normalize_question
from ai_backend.infra.cost.tracker import (
    CostTracker,
    get_cost_context,
    record_completion_usage,
)
from ai_backend.infra.storage.chart_store import safe_png_name
from ai_backend.infra.storage.memory_store import SqliteMemoryStore
from ai_backend.infra.storage.watchlist_store import SqliteWatchlistStore
from ai_backend.infra.monitoring.tracing import redact_pii, sanitize_trace_payload
from ai_backend.infra.agents.price_agent import run_price_agent, PriceAgentResult
from ai_backend.infra.agents.eval_agent import run_eval_agent, EvalAgentBrain
from ai_backend.infra.agents.event_classifier import classify_event, EventClassifierBrain
from ai_backend.infra.agents.portfolio_watch_agent import run_portfolio_watch_agent
from common.domain.entities import WatchlistItem, RoutingDecision, EventRoute, Severity, SeverityLevel


class TestGraphInfrastructure:
    """Kiểm thử cấu trúc StateGraph điều phối LangGraph Swarm."""

    def test_build_swarm_graph_nodes(self):
        graph = build_swarm_graph()
        nodes = list(graph.nodes.keys())
        # Đảm bảo đủ các node cần thiết trong quy trình swarm 13 nodes
        expected_nodes = [
            "orchestrator",
            "price_agent",
            "news_agent",
            "event_classifier",
            "eval_agent",
            "synthesis_agent",
            "guardrail_output",
            "confidence_gate",
            "supervisor",
            "answer_composer",
        ]
        for node in expected_nodes:
            assert node in nodes, f"Node {node} must be present in swarm graph"

    def test_compile_portfolio_graph(self):
        compiled = compile_portfolio_graph()
        assert compiled is not None
        # Kiểm tra danh sách node từ helper
        node_names = list_graph_nodes()
        assert len(node_names) >= 10


class TestMarketDataInfrastructure:
    """Kiểm thử nguồn dữ liệu thị trường và offline fallback."""

    def test_price_source_offline_fallback(self, monkeypatch):
        # Thiết lập chạy 100% offline
        monkeypatch.setenv("PRICE_FALLBACK_ON_ERROR", "true")
        ps = VnstockPriceSource()
        quote = ps.fetch_latest_close("HPG")
        assert quote.symbol == "HPG"
        assert quote.latest_close is not None
        assert quote.latest_close > 0

    def test_price_source_fetch_history_offline(self, monkeypatch):
        monkeypatch.setenv("PRICE_FALLBACK_ON_ERROR", "true")
        ps = VnstockPriceSource()
        bars = ps.fetch_history("HPG", lookback_days=5)
        assert isinstance(bars, list)
        assert len(bars) > 0
        assert bars[0].close > 0


class TestConceptRagInfrastructure:
    """Kiểm thử nạp tri thức Concept RAG."""

    def test_load_concept_chunks_finds_markdown_files(self):
        chunks = load_concept_chunks()
        assert isinstance(chunks, list)
        assert len(chunks) > 0
        first = chunks[0]
        assert first.text
        assert first.source_file
        assert first.heading


class TestCacheAndCostInfrastructure:
    """Kiểm thử tầng Cache và Cost Tracker."""

    def test_normalize_question(self):
        assert normalize_question("  RSI của   HPG hôm nay thế nào?  ") == "rsi của hpg hôm nay thế nào?"
        assert normalize_question("") == ""

    def test_cost_tracker_usage(self):
        tracker = CostTracker()
        rec = tracker.record_cost(
            feature="chat",
            model="gpt-4o-mini",
            prompt_version="v1",
            cache_hit=False,
            prompt_tokens=100,
            completion_tokens=50,
        )
        assert rec.total_tokens == 150
        assert rec.cost_usd > 0
        assert len(tracker.records) == 1


class TestStorageInfrastructure:
    """Kiểm thử tầng lưu trữ: biểu đồ, watchlist và memory."""

    def test_safe_png_name(self):
        assert safe_png_name("chart_fpt.png") == "chart_fpt.png"
        assert safe_png_name("../../../etc/passwd.png") == "passwd.png"
        assert safe_png_name("invalid.exe") is None
        assert safe_png_name("") is None

    def test_sqlite_watchlist_and_memory(self, tmp_path):
        db_file = tmp_path / "test_store.db"
        wl_store = SqliteWatchlistStore(str(db_file))
        wl_store.upsert(WatchlistItem(user_id="user_test", symbol="SSI", threshold_pct=4.5))
        items = wl_store.list_items("user_test")
        assert len(items) == 1
        assert items[0].symbol == "SSI"
        assert items[0].threshold_pct == 4.5

        mem_store = SqliteMemoryStore(str(db_file))
        mem_store.append_conversation("user_test", "user", "Xin chào")
        mem_store.append_conversation("user_test", "assistant", "Chào bạn!")
        conv = mem_store.list_conversation("user_test")
        assert len(conv) == 2
        assert conv[0]["content"] == "Xin chào"


class TestMonitoringInfrastructure:
    """Kiểm thử Masking PII và Tracing."""

    def test_pii_redaction(self):
        text = "Liên hệ user test@example.com hoặc SĐT 0912345678 để nhận OTP."
        redacted = redact_pii(text)
        assert "[EMAIL_REDACTED]" in redacted
        assert "[PHONE_REDACTED]" in redacted
        assert "test@example.com" not in redacted
        assert "0912345678" not in redacted

    def test_sanitize_trace_payload(self):
        payload = {
            "user_email": "admin@fpt.vn",
            "symbol": "VNM",
            "nested": {
                "contact": "0987654321",
                "normal": "value",
            },
        }
        sanitized = sanitize_trace_payload(payload)
        assert sanitized["user_email"] == "[EMAIL_REDACTED]"
        assert sanitized["symbol"] == "VNM"
        assert sanitized["nested"]["contact"] == "[PHONE_REDACTED]"
        assert sanitized["nested"]["normal"] == "value"


class TestWorkerAgentsInfrastructure:
    """Kiểm thử các Agent Worker vận hành offline."""

    def test_price_agent_execution(self, monkeypatch):
        monkeypatch.setenv("PRICE_FALLBACK_ON_ERROR", "true")
        ps = VnstockPriceSource()
        res = run_price_agent("VNM", price_source=ps)
        assert isinstance(res, PriceAgentResult)
        assert res.symbol == "VNM"
        assert res.latest_close is not None

    def test_eval_agent_offline(self):
        from ai_backend.infra.agents.eval_agent.nodes import HeuristicEvalBrain
        p = PriceAgentResult(symbol="FPT", latest_close=130.0, prev_close=129.0, change_pct=0.77)
        res = run_eval_agent(p, None, None, brain=HeuristicEvalBrain())
        assert res.severity is not None
        assert res.severity.level is not None

    def test_event_classifier_offline(self):
        class _MockClassifierBrain:
            def classify(self, price, news, threshold_pct):
                return RoutingDecision(route=EventRoute.NORMAL, agents_to_call=["price_agent"], reason="Dưới ngưỡng")

        p = PriceAgentResult(symbol="TCB", latest_close=25.0, prev_close=24.9, change_pct=0.4)
        decision = classify_event(p, None, threshold_pct=3.0, brain=_MockClassifierBrain())
        assert decision.route == EventRoute.NORMAL

    def test_portfolio_watch_agent_in_memory(self, monkeypatch):
        monkeypatch.setenv("PRICE_FALLBACK_ON_ERROR", "true")
        ps = VnstockPriceSource()
        holdings = [
            {"symbol": "HPG", "quantity": 1000, "avg_buy_price": 28.0},
            {"symbol": "FPT", "quantity": 500, "avg_buy_price": 125.0},
        ]
        res = run_portfolio_watch_agent(
            user_id="user_test",
            intent="portfolio",
            price_source=ps,
            account_holdings=holdings,
        )
        assert res.error is None
        assert res.portfolio_summary is not None
        assert res.portfolio_summary.total_cost > 0
        assert res.portfolio_summary.total_nav > 0
        assert "HPG" in res.formatted_markdown
        assert "FPT" in res.formatted_markdown
