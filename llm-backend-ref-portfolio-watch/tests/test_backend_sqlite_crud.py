"""Phase 4 — Watchlist/approvals CRUD qua Backend; SQLite Backend sở hữu dữ liệu."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app, store
from backend.store import ApprovalRecord, Store, WatchlistItem

FE = Path(__file__).resolve().parents[1] / "frontend"


def setup_function():
    store.clear()


def test_sqlite_watchlist_persists_across_store_instances(tmp_path):
    db = str(tmp_path / "backend_store.db")
    a = Store(db_path=db)
    a.upsert_watchlist(WatchlistItem(symbol="HPG", threshold_pct=2.5))
    a.add_pending(
        ApprovalRecord(id="p1", user_id="default", symbol="HPG", gate="gate1")
    )

    b = Store(db_path=db)
    items = b.list_watchlist("default")
    assert len(items) == 1
    assert items[0].symbol == "HPG"
    assert items[0].threshold_pct == 2.5
    pending = b.list_pending("default")
    assert len(pending) == 1
    assert pending[0].id == "p1"


def test_api_crud_and_approvals_survive_reload_pattern(tmp_path, monkeypatch):
    """CRUD qua API; dữ liệu nằm trong SQLite Backend (không AI)."""
    client = TestClient(app)
    store.clear()

    created = client.post(
        "/watchlist", json={"symbol": "VNM", "threshold_pct": 5.0}
    )
    assert created.status_code == 200
    patched = client.patch("/watchlist/VNM", json={"threshold_pct": 4.5})
    assert patched.json()["threshold_pct"] == 4.5

    # Persist: mở Store cùng path với store đang dùng
    again = Store(db_path=store.db_path)
    got = again.get_watchlist("default", "VNM")
    assert got is not None and got.threshold_pct == 4.5

    store.add_pending(
        ApprovalRecord(id="ap-x", user_id="default", symbol="VNM", gate="gate1")
    )
    assert client.post("/approvals/ap-x/approve", json={}).status_code == 200
    again2 = Store(db_path=store.db_path)
    assert again2.list_pending("default") == []
    # approved row vẫn còn trong DB (status đổi)
    row = again2._conn.execute(
        "SELECT status FROM approvals WHERE id = ?", ("ap-x",)
    ).fetchone()
    assert row["status"] == "approved"

    assert client.delete("/watchlist/VNM").status_code == 200
    assert Store(db_path=store.db_path).get_watchlist("default", "VNM") is None


def test_frontend_crud_calls_include_patch():
    js = (FE / "app.js").read_text(encoding="utf-8")
    assert 'api("POST", "/watchlist"' in js or "/watchlist" in js
    assert "PATCH" in js
    assert "/approvals/" in js and "approve" in js and "reject" in js
    assert "doPatchWatch" in js
    assert "8001" not in js
