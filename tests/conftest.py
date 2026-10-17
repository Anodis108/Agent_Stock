"""Pytest Shared Fixtures — Portfolio Watch (Clean & Unified Test Suite).

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

from ai_backend.main import app as ai_app
from web_backend.api.deps import AppDeps, clear_deps_cache, set_app_deps
from common.domain.entities import WatchlistItem
from ai_backend.infra.market_data import CafefNewsSource, VnstockPriceSource
from ai_backend.infra.notify import ConsoleNotifier
from ai_backend.infra.storage import (
    PgMemoryStore,
    PgPriceHistoryStore,
    PgWatchlistStore,
)
from ai_backend.shared.settings import ai_settings
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


def build_real_deps(schema: str) -> AppDeps:
    """Khởi tạo AppDeps chuẩn production phục vụ kiểm thử."""
    from web_backend.infra.database.connection import get_connection
    from web_backend.infra.database.repositories import (
        PortfolioHoldingRepository,
        UserSettingsRepository,
    )
    conn = get_connection(schema)
    memory = PgMemoryStore(schema)
    deps = AppDeps(
        price_source=VnstockPriceSource(fallback_on_error=True),
        news_source=CafefNewsSource(),
        history_store=PgPriceHistoryStore(schema),
        memory_store=memory,
        notifier=ConsoleNotifier(memory),
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
    monkeypatch.setenv("PRICE_FALLBACK_ON_ERROR", "true")
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
    monkeypatch.setenv("PRICE_FALLBACK_ON_ERROR", "true")
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
