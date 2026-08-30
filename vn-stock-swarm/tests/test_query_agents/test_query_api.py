"""Test end-to-end luồng HITL 2-step qua HTTP: POST /ask có thể dừng ở
"pending_approval", và chỉ POST /approve mới thật sự commit dữ liệu.

Không chạy `_lifespan` thật (nó cần Redis thật qua get_redis()) — thay vào đó
gán thẳng module-level `_coordinator` bằng 1 QueryCoordinator dùng SinkStore
tạm + Redis giả (fixture `redis`), rồi gọi qua ASGITransport. Đây là ranh giới
hợp lý cho demo: kiểm tra đúng hợp đồng HTTP (request/response shape, status
code), không kiểm tra lại lifespan wiring (không có gì đặc biệt để kiểm tra ở đó).
"""

from __future__ import annotations

from pathlib import Path

import httpx

from config import Settings
from query import api as query_api
from query.coordinator import QueryCoordinator
from sink_store import SinkStore


def _settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "coordinator_poll_timeout_seconds": 0.2,
        "coordinator_poll_interval_seconds": 0.05,
        "price_staleness_seconds": 900.0,
        "news_freshness_seconds": 7200.0,
    }
    defaults.update(overrides)
    return Settings(**defaults)


async def _client(redis, tmp_path: Path) -> httpx.AsyncClient:
    store = SinkStore(str(tmp_path / "sink.db"))
    query_api._coordinator = QueryCoordinator(store, redis, _settings())
    transport = httpx.ASGITransport(app=query_api.app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


async def test_ask_without_new_news_answers_directly(redis, tmp_path: Path) -> None:
    """Không có tin mới cần duyệt → /ask trả status="answered" ngay trong 1 lượt gọi."""
    async with await _client(redis, tmp_path) as client:
        store = query_api._coordinator._store  # type: ignore[union-attr]
        await store.save_price("HPG", "https://api.ssi.com.vn/hpg", {"close": "28000"})
        await store.save_news(["HPG"], "HPG tăng trần phiên sáng", "https://cafef.vn/hpg-news")

        resp = await client.post("/ask", json={"question": "Giá HPG hôm nay bao nhiêu?"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "answered"
        assert body["symbol"] == "HPG"


async def test_ask_with_new_news_pauses_then_approve_commits(redis, tmp_path: Path) -> None:
    """Luồng đầy đủ: /ask thấy tin mới → pending_approval → /approve
    (approve=True) → status="answered" + tin đã thật sự vào SinkStore."""
    async with await _client(redis, tmp_path) as client:
        store = query_api._coordinator._store  # type: ignore[union-attr]
        await store.save_price("HPG", "https://api.ssi.com.vn/hpg", {"close": "28000"})
        await store.save_news_pending(["HPG"], "HPG giảm sàn phiên sáng", "https://cafef.vn/hpg-a")

        ask_resp = await client.post("/ask", json={"question": "Giá HPG hôm nay bao nhiêu?"})
        assert ask_resp.status_code == 200
        ask_body = ask_resp.json()
        assert ask_body["status"] == "pending_approval"
        assert ask_body["request_id"] is not None
        assert len(ask_body["pending_writes"]) == 1

        approve_resp = await client.post(
            "/approve", json={"request_id": ask_body["request_id"], "approve": True}
        )
        assert approve_resp.status_code == 200
        approve_body = approve_resp.json()
        assert approve_body["status"] == "answered"
        assert await store.has_recent_news("HPG", within_seconds=3600) is True


async def test_approve_with_unknown_request_id_returns_404(redis, tmp_path: Path) -> None:
    async with await _client(redis, tmp_path) as client:
        resp = await client.post("/approve", json={"request_id": "khong-ton-tai", "approve": True})
        assert resp.status_code == 404


async def test_health_endpoint(redis, tmp_path: Path) -> None:
    async with await _client(redis, tmp_path) as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
