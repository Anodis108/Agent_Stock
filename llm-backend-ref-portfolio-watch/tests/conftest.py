"""Pytest Shared Fixtures — Portfolio Watch (Clean & Unified Test Suite).

Cung cấp các fixture chuẩn:
- `real_deps`: Wiring các dependency thật (Vnstock, CafeF, SQLite memory, watchlist).
- `client`: FastAPI TestClient kết nối với database tạm thời cô lập.
- `ai_server_url`: AI Swarm service phục vụ kiểm thử HTTP proxy.
"""

from __future__ import annotations

import socket
import threading
import time
from pathlib import Path

import pytest
import uvicorn
from fastapi.testclient import TestClient

from backend.ai_main import app as ai_app
from backend.api.deps import AppDeps, clear_deps_cache, set_app_deps
from backend.domain.entities import WatchlistItem
from backend.infra.market_data import CafefNewsSource, VnstockPriceSource
from backend.infra.notify import ConsoleNotifier
from backend.infra.storage import (
    SqliteMemoryStore,
    SqlitePriceHistoryStore,
    SqliteWatchlistStore,
)
from backend.main import app as main_app


def build_real_deps(db_path: str) -> AppDeps:
    """Khởi tạo AppDeps chuẩn production phục vụ kiểm thử."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    memory = SqliteMemoryStore(db_path)
    deps = AppDeps(
        price_source=VnstockPriceSource(),
        news_source=CafefNewsSource(),
        history_store=SqlitePriceHistoryStore(db_path),
        memory_store=memory,
        notifier=ConsoleNotifier(memory),
        watchlist_store=SqliteWatchlistStore(db_path),
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
def real_deps(tmp_path, monkeypatch):
    """SQLite tạm thời + nguồn giá/tin thật cho từng bài kiểm thử agent/graph."""
    db = tmp_path / "portfolio_watch.db"
    monkeypatch.setenv("SQLITE_PATH", str(db))
    monkeypatch.setenv("BACKEND_SQLITE_PATH", str(tmp_path / "backend_store.db"))
    clear_deps_cache()
    deps = build_real_deps(str(db))
    set_app_deps(deps)
    yield deps
    set_app_deps(None)
    clear_deps_cache()


@pytest.fixture
def client(tmp_path, monkeypatch):
    """TestClient kết nối tới app FastAPI với database tạm thời cô lập."""
    temp_db = tmp_path / "test_api.db"
    monkeypatch.setenv("SQLITE_PATH", str(temp_db))
    monkeypatch.setenv("BACKEND_SQLITE_PATH", str(tmp_path / "test_store.db"))
    clear_deps_cache()
    deps = build_real_deps(str(temp_db))
    set_app_deps(deps)
    c = TestClient(main_app)
    yield c
    set_app_deps(None)
    clear_deps_cache()


@pytest.fixture(scope="session")
def ai_server_url(tmp_path_factory):
    """AI service thật trên port ngẫu nhiên phục vụ kiểm thử HTTP proxy."""
    base = tmp_path_factory.mktemp("ai_server")
    db = base / "ai.db"
    clear_deps_cache()
    set_app_deps(build_real_deps(str(db)))
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
