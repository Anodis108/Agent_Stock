from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from src.portfolio_watch.domain.entities import WatchlistItem
from src.portfolio_watch.domain.ports import PriceBar
from src.portfolio_watch.infra.storage import (
    SqliteMemoryStore,
    SqlitePriceHistoryStore,
    SqliteWatchlistStore,
)


def test_sqlite_stores_roundtrip(tmp_path: Path):
    db = str(tmp_path / "test.db")
    watch = SqliteWatchlistStore(db)
    hist = SqlitePriceHistoryStore(db)
    mem = SqliteMemoryStore(db)

    item = watch.upsert(WatchlistItem(symbol="fpt", threshold_pct=3.5))
    assert item.symbol == "FPT"
    assert watch.get("default", "FPT") is not None
    assert len(watch.list_items()) == 1

    today = date.today()
    hist.upsert_bars(
        "FPT",
        [
            PriceBar(date=(today - timedelta(days=2)).isoformat(), close=100.0),
            PriceBar(date=(today - timedelta(days=1)).isoformat(), close=98.0),
        ],
    )
    bars = hist.read_history("FPT", days=7)
    assert len(bars) == 2
    assert bars[-1].close == 98.0

    mem.write_preferences("default", {"tone": "ngắn"})
    assert mem.read_preferences()["tone"] == "ngắn"
    mem.append_conversation("default", "user", "FPT sao rồi?")
    mem.append_conversation("default", "assistant", "Đang theo dõi.")
    assert len(mem.list_conversation("default")) == 2
    mem.append_alert_event("default", {"symbol": "FPT", "status": "sent"})
    assert mem.list_alert_events("default")[0]["symbol"] == "FPT"
    mem.record_rejection(
        "default",
        gate="gate1",
        reason="ngưỡng sai",
        context={"alert_id": "a1"},
    )
    rejections = mem.list_rejections("default")
    assert len(rejections) == 1
    assert rejections[0]["reason"] == "ngưỡng sai"
    assert rejections[0]["gate"] == "gate1"
    assert rejections[0]["context"]["alert_id"] == "a1"

    # Gate 2 reject: không gọi upsert → cấu hình cũ giữ nguyên
    before = watch.get("default", "FPT")
    assert before is not None and before.threshold_pct == 3.5
    mem.record_rejection("default", gate="gate2", reason="giữ ngưỡng cũ")
    after = watch.get("default", "FPT")
    assert after is not None and after.threshold_pct == 3.5

    assert watch.delete("default", "FPT") is True
    assert watch.get("default", "FPT") is None
