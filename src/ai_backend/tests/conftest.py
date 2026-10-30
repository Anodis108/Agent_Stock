"""Pytest Shared Fixtures for AI Backend test suite.

Cung cấp các fixture chuẩn:
- `pg_schema`: Schema PostgreSQL tạm thời, xóa sau mỗi bài kiểm thử.
- `real_deps`: Wiring các dependency thật (Vnstock, CafeF, PostgreSQL memory, watchlist).
- `client`: FastAPI TestClient kết nối với database tạm thời cô lập.
- `ai_server_url`: AI Swarm service phục vụ kiểm thử HTTP proxy.
"""

from __future__ import annotations

import socket
import threading
import time
import uuid

import psycopg
import pytest
import uvicorn
from fastapi.testclient import TestClient

from ai_backend.infra.market_data import CafefNewsSource, VnstockPriceSource
from ai_backend.infra.notify import ConsoleNotifier
from ai_backend.infra.storage import (
    PgMemoryStore,
    PgPriceHistoryStore,
    PgWatchlistStore,
)
from ai_backend.main import app as ai_app
from ai_backend.shared.settings import ai_settings
from common.domain.entities import WatchlistItem
from web_backend.api.deps import AppDeps, clear_deps_cache, set_app_deps
from web_backend.infra.database.connection import get_connection
from web_backend.infra.database.repositories import (
    PortfolioHoldingRepository,
    UserSettingsRepository,
)
from web_backend.main import app as main_app


def _new_pg_schema() -> str:
    return f"test_{uuid.uuid4().hex[:12]}"


def _drop_pg_schema(schema: str) -> None:
    if not ai_settings.database_url:
        return
    with psycopg.connect(ai_settings.database_url, autocommit=True) as conn:
        conn.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')


@pytest.fixture(autouse=True)
def _pg_test_schema(monkeypatch):
    """Mọi bài kiểm thử dùng schema PostgreSQL tạm (cả get_connection của web_backend), xóa khi kết thúc."""
    from web_backend.infra.database import connection

    schema = _new_pg_schema()
    monkeypatch.setattr(connection, "DEFAULT_SCHEMA", schema)
    yield schema
    _drop_pg_schema(schema)


@pytest.fixture
def pg_schema(_pg_test_schema):
    """Schema PostgreSQL tạm của bài kiểm thử; skip nếu thiếu DATABASE_URL."""
    if not ai_settings.database_url:
        pytest.skip("Cần DATABASE_URL để chạy kiểm thử PostgreSQL")
    return _pg_test_schema


class OfflineQuote:
    """Thay `vnstock.Quote` khi test offline: 30 phiên nến cố định theo mã; mã lạ -> lỗi như vnstock thật."""

    BASE_PRICES = {
        "FPT": 66.0, "VNM": 61.0, "HPG": 21.0, "VHM": 66.0, "VIC": 45.0,
        "TCB": 33.0, "MBB": 20.0, "SSI": 21.0, "MWG": 73.0, "VCB": 58.0,
    }

    def __init__(self, symbol: str, source: str | None = None):
        self.symbol = symbol

    def history(self, start: str, end: str, interval: str = "1D"):
        import pandas as pd

        if self.symbol not in self.BASE_PRICES:
            raise ValueError(f"symbol {self.symbol} not found")
        base = self.BASE_PRICES[self.symbol]
        days = pd.bdate_range(end=end, periods=30)
        closes = [round(base * (1 + ((i % 7) - 3) * 0.004), 2) for i in range(len(days))]
        return pd.DataFrame({
            "time": days,
            "open": [round(c * 0.995, 2) for c in closes],
            "high": [round(c * 1.01, 2) for c in closes],
            "low": [round(c * 0.99, 2) for c in closes],
            "close": closes,
            "volume": [1_000_000 + i * 10_000 for i in range(len(days))],
        })


def offline_price_source() -> VnstockPriceSource:
    """VnstockPriceSource thật nhưng nguồn dữ liệu là OfflineQuote (không gọi mạng)."""
    return VnstockPriceSource(quote_factory=OfflineQuote)


@pytest.fixture
def offline_prices() -> VnstockPriceSource:
    return offline_price_source()


def build_real_deps(schema: str) -> AppDeps:
    """Khởi tạo AppDeps chuẩn production phục vụ kiểm thử (giá lấy từ OfflineQuote)."""
    conn = get_connection(schema)
    memory = PgMemoryStore(schema)
    deps = AppDeps(
        price_source=offline_price_source(),
        news_source=CafefNewsSource(),
        history_store=PgPriceHistoryStore(schema),
        memory_store=memory,
        notifier=ConsoleNotifier(memory, user_id="default"),
        watchlist_store=PgWatchlistStore(schema),
        holdings_repo=PortfolioHoldingRepository(conn),
        user_settings_repo=UserSettingsRepository(conn),
    )
    deps.watchlist_store.upsert(
        WatchlistItem(symbol="FPT", threshold_pct=3.0, user_id="default")
    )
    return deps


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def real_deps(monkeypatch, pg_schema):
    """PostgreSQL schema tạm thời + nguồn giá/tin thật cho từng bài kiểm thử agent/graph."""
    monkeypatch.setenv("MONITORING_ENABLED", "false")
    monkeypatch.setenv("LLM_MAX_RETRIES", "1")
    clear_deps_cache()
    deps = build_real_deps(pg_schema)
    set_app_deps(deps)
    yield deps
    set_app_deps(None)
    clear_deps_cache()


@pytest.fixture
def client(monkeypatch, pg_schema):
    """TestClient kết nối tới app FastAPI với database tạm thời cô lập."""
    monkeypatch.setenv("MONITORING_ENABLED", "false")
    monkeypatch.setenv("LLM_MAX_RETRIES", "1")
    clear_deps_cache()
    deps = build_real_deps(pg_schema)
    set_app_deps(deps)
    c = TestClient(main_app)
    yield c
    set_app_deps(None)
    clear_deps_cache()


@pytest.fixture(scope="session")
def ai_server_url():
    """AI service thật trên port ngẫu nhiên phục vụ kiểm thử HTTP proxy."""
    schema = _new_pg_schema()
    clear_deps_cache()
    set_app_deps(build_real_deps(schema))
    port = _free_port()
    config = uvicorn.Config(ai_app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{port}"
    for _ in range(50):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                break
        except OSError:
            time.sleep(0.1)
    else:
        pytest.fail("AI test server không khởi động được")
    yield url
    set_app_deps(None)
    clear_deps_cache()
    _drop_pg_schema(schema)


@pytest.fixture
def fake_scan_runner():
    """Factory runner giả thay run_scan_graph (test double, không mạng / LLM): trả kết quả scan dựng sẵn."""
    from ai_backend.domain.agents.scan.news_agent.state import NewsAgentResult
    from ai_backend.domain.agents.scan.price_agent.state import PriceAgentResult
    from ai_backend.domain.agents.scan.state import ScanSymbolResult
    from common.domain.entities import EventRoute, RoutingDecision

    def make(change_pct: float = -6.0, abnormal: bool = True):
        def runner(symbol, **kwargs):
            route = EventRoute.ABNORMAL if abnormal else EventRoute.NORMAL
            syms = [symbol] if isinstance(symbol, str) else [str(s) for s in symbol]
            ticker = syms[0] if syms else ""
            return ScanSymbolResult(
                symbol=syms,
                price=[
                    PriceAgentResult(
                        symbol=ticker, latest_close=100.0 + change_pct, prev_close=100.0, change_pct=change_pct
                    )
                ],
                news=[NewsAgentResult(symbol=ticker, items=[])],
                routing=RoutingDecision(route=route, reason=f"giả lập {route.value}"),
                threshold_pct=kwargs.get("threshold_pct") or 3.0,
                steps=[
                    {"id": "1", "name": "price_agent", "status": "done"},
                    {"id": "2", "name": "event_classifier", "status": "done"},
                ],
            )

        return runner

    return make


@pytest.fixture
def fake_chat_runner():
    """Runner giả thay run_chat_graph (test double): phát event như graph thật rồi trả kết quả dựng sẵn."""
    from ai_backend.domain.agents.chat.chat_supervisor_agent.nodes import RewrittenQuestion
    from ai_backend.domain.agents.state import AnswerQuestionResult
    from common.domain.entities import RoutingDecision

    def runner(question, event_callback=None, **_kwargs):
        answer = f"Trả lời giả cho: {question}"
        if event_callback:
            event_callback("node_start", {"node": "answer_composer"})
            for word in answer.split(" "):
                event_callback("token", {"delta": word + " "})
            event_callback("node_finish", {"node": "answer_composer"})
        return AnswerQuestionResult(
            question=question,
            rewritten=RewrittenQuestion(
                original=question,
                rewritten=question,
                symbol=None,
                intent="explain",
            ),
            routing=RoutingDecision(route="general"),
            answer=answer,
            steps=[{"id": "1", "name": "answer_composer", "status": "done"}],
        )

    return runner
