"""Pytest — dependency thật (vnstock, Cafef, SQLite, LLM production)."""

from __future__ import annotations

import socket
import threading
import time
from pathlib import Path

import pytest
import uvicorn

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


def build_real_deps(db_path: str) -> AppDeps:
    """Cùng wiring production — deps.py."""
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
    """SQLite tạm + nguồn giá/tin thật cho từng test AI/graph."""
    db = tmp_path / "portfolio_watch.db"
    monkeypatch.setenv("SQLITE_PATH", str(db))
    clear_deps_cache()
    deps = build_real_deps(str(db))
    set_app_deps(deps)
    yield deps
    set_app_deps(None)
    clear_deps_cache()


@pytest.fixture(scope="session")
def ai_server_url(tmp_path_factory):
    """AI service thật trên port ngẫu nhiên — Backend gọi HTTP thật."""
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
