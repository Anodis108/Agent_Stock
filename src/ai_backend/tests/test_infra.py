"""Unit tests for AI Backend Infrastructure Layer (ai_backend.infra).

Tests:
- Graph orchestration: build_graph
- Market data: VnstockPriceSource with offline fallback
- Qdrant/Concept loading: load_concept_chunks from resources/concepts
- Cache layer: normalize_question, ExactCache context
- Cost tracker: record_completion_usage, get_cost_context
- Storage layer: ChartObjectStore, safe_png_name, PgMemoryStore, PgWatchlistStore
- Worker Agents: all 10 worker agents offline execution
- PortfolioWatchAgent: in-memory calculation with account_holdings snapshot
"""

from __future__ import annotations


from ai_backend.domain.agents.graph import build_graph
from ai_backend.infra.market_data.price_source import VnstockPriceSource
from ai_backend.infra.qdrant.concepts import load_concept_chunks
from ai_backend.infra.cache.exact import normalize_question
from ai_backend.infra.cost.tracker import (
    CostTracker,
)
from ai_backend.infra.storage.chart_store import safe_png_name
from ai_backend.infra.storage.memory_store import PgMemoryStore
from ai_backend.infra.storage.watchlist_store import PgWatchlistStore
from ai_backend.domain.agents.scan.price_agent import run_price_agent, PriceAgentResult
from ai_backend.domain.agents.scan.eval_agent import run_eval_agent
from ai_backend.domain.agents.chat.nodes.portfolio import run_portfolio_watch
from common.domain.entities import WatchlistItem


class TestGraphInfrastructure:
    """Kiểm thử cấu trúc StateGraph điều phối LangGraph Swarm."""

    def test_swarm_graph_compiles(self):
        g = build_graph().get_graph()
        assert {"top_supervisor", "chat_team", "scan_team"} <= set(g.nodes.keys())

    def test_swarm_subgraph_nodes_visible_with_xray(self):
        nodes = set(build_graph().get_graph(xray=1).nodes.keys())
        assert {"guardrail_input", "scan_supervisor", "event_classifier", "scan_tools"} <= nodes


class TestMarketDataInfrastructure:
    """Kiểm thử nguồn dữ liệu thị trường (OfflineQuote thay vnstock trong test)."""

    def test_price_source_parses_quote_history(self, offline_prices):
        quote = offline_prices.fetch_latest_close("HPG")
        assert quote.symbol == "HPG"
        assert quote.error is None
        assert quote.latest_close is not None and quote.latest_close > 0
        assert quote.prev_close is not None

    def test_price_source_source_error_returns_error_not_fake_price(self):
        class DownQuote:
            def __init__(self, symbol, source=None):
                pass

            def history(self, **_kwargs):
                raise ConnectionError("connection refused")

        quote = VnstockPriceSource(quote_factory=DownQuote).fetch_latest_close("HPG")
        assert quote.latest_close is None
        assert "kết nối" in (quote.error or "")

    def test_price_source_fetch_history_offline(self, offline_prices):
        bars = offline_prices.fetch_history("HPG", lookback_days=5)
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

    def test_pg_watchlist_and_memory(self, pg_schema):
        wl_store = PgWatchlistStore(pg_schema)
        wl_store.upsert(WatchlistItem(user_id="user_test", symbol="SSI", threshold_pct=4.5))
        items = wl_store.list_items("user_test")
        assert len(items) == 1
        assert items[0].symbol == "SSI"
        assert items[0].threshold_pct == 4.5

        mem_store = PgMemoryStore(pg_schema)
        mem_store.append_conversation("user_test", "user", "Xin chào")
        mem_store.append_conversation("user_test", "assistant", "Chào bạn!")
        conv = mem_store.list_conversation("user_test")
        assert len(conv) == 2
        assert conv[0]["content"] == "Xin chào"


class TestWorkerAgentsInfrastructure:
    """Kiểm thử các Agent Worker vận hành offline."""

    def test_price_agent_execution(self, offline_prices):
        res = run_price_agent("VNM", price_source=offline_prices)
        assert isinstance(res, PriceAgentResult)
        assert res.symbol == "VNM"
        assert res.latest_close is not None

    def test_eval_agent_offline(self):
        from ai_backend.domain.agents.scan.eval_agent.nodes import HeuristicEvalBrain
        p = PriceAgentResult(symbol="FPT", latest_close=130.0, prev_close=129.0, change_pct=0.77)
        res = run_eval_agent(p, None, None, brain=HeuristicEvalBrain())
        assert res.severity is not None
        assert res.severity.level is not None

    def test_portfolio_watch_in_memory(self, offline_prices):
        ps = offline_prices
        holdings = [
            {"symbol": "HPG", "quantity": 1000, "avg_buy_price": 28.0},
            {"symbol": "FPT", "quantity": 500, "avg_buy_price": 125.0},
        ]
        res = run_portfolio_watch(
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
