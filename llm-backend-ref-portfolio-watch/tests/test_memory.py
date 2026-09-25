"""Kiểm thử Hệ thống Bộ nhớ (Memory) và Quản lý Phiên hội thoại (Sessions).

Bao gồm:
1. Short-Term Memory: Cửa sổ trượt (Sliding Window), thời gian sống (TTL), kế thừa ngữ cảnh Turn 1 ➔ Turn 2.
2. Long-Term Memory: Lưu trữ fact, cô lập người dùng (User Isolation), Vector store fallback.
3. Session & Message Persistence: CRUD session, phân nhánh hội thoại, xóa cascade, tự động đặt tiêu đề.
"""

from __future__ import annotations

import datetime
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from backend.agents.supervisor_agent.nodes import (
    HeuristicRewriteBrain,
    HeuristicSupervisorBrain,
    recall_memory,
    rewrite_question,
    store_memory,
)
from backend.database.connection import get_connection, init_db
from backend.database.repositories import MessageRepository, SessionRepository
from backend.graph.chat import run_chat_graph
from backend.infra.storage.memory_store import (
    SqliteMemoryStore,
    filter_conversation_history,
    parse_timestamp,
)
from backend.main import app as product_app


# ==============================================================================
# 1. Short-Term Memory Tests (Sliding Window, TTL, Turn 1 -> Turn 2)
# ==============================================================================

def test_parse_timestamp_formats():
    """Kiểm tra parse timestamp hỗ trợ cả datetime object, ISO format và space format."""
    now = datetime.datetime.now(datetime.timezone.utc)
    assert parse_timestamp(now) is not None
    assert parse_timestamp("2026-09-25T10:00:00+00:00") is not None
    assert parse_timestamp("2026-09-25 10:00:00") is not None


def test_filter_conversation_history_sliding_window():
    """Kiểm tra cửa sổ trượt chỉ giữ lại N tin nhắn gần nhất."""
    history = [
        {"role": "user", "content": f"msg {i}", "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
        for i in range(10)
    ]
    filtered = filter_conversation_history(history, limit=4, ttl_minutes=60)
    assert len(filtered) == 4
    assert filtered[-1]["content"] == "msg 9"
    assert filtered[0]["content"] == "msg 6"


def test_filter_conversation_history_ttl_expiry():
    """Kiểm tra các tin nhắn quá hạn TTL (> 30 phút) bị loại bỏ khỏi ngữ cảnh."""
    now = datetime.datetime.now(datetime.timezone.utc)
    old_time = (now - datetime.timedelta(minutes=45)).isoformat()
    new_time = (now - datetime.timedelta(minutes=5)).isoformat()

    history = [
        {"role": "user", "content": "Tin nhắn cũ hết hạn", "created_at": old_time},
        {"role": "user", "content": "Tin nhắn mới còn hạn", "created_at": new_time},
    ]
    filtered = filter_conversation_history(history, limit=10, ttl_minutes=30)
    assert len(filtered) == 1
    assert filtered[0]["content"] == "Tin nhắn mới còn hạn"


def test_followup_resolves_symbol_in_window(real_deps):
    """Kiểm tra câu hỏi nối tiếp (Follow-up Turn 2: 'Tại sao lại giảm?') kế thừa đúng mã FPT từ Turn 1."""
    # Turn 1
    real_deps.memory_store.append_conversation("user_test", "user", "Cổ phiếu FPT hôm nay thế nào?")
    real_deps.memory_store.append_conversation("user_test", "assistant", "FPT giảm 1.5% xuống 120.0.")

    # Turn 2
    conv = real_deps.memory_store.list_conversation("user_test", limit=5, ttl_minutes=30)
    rewritten = rewrite_question("Tại sao lại giảm?", conv, brain=HeuristicRewriteBrain())
    assert rewritten.symbol == "FPT"
    assert "FPT" in rewritten.rewritten


def test_turn1_turn2_chat_flow_end_to_end(real_deps):
    """Kiểm tra luồng hội thoại 2 lượt hoàn chỉnh qua run_chat_graph."""
    # Turn 1: Hỏi giá FPT
    res1 = run_chat_graph(
        "FPT giá bao nhiêu?",
        price_source=real_deps.price_source,
        news_source=real_deps.news_source,
        history_store=real_deps.history_store,
        memory_store=real_deps.memory_store,
        rewrite_brain=HeuristicRewriteBrain(),
        supervisor_brain=HeuristicSupervisorBrain(),
        user_id="user_flow",
        turn="turn_1",
    )
    assert res1.rewritten.symbol == "FPT"

    # Turn 2: Hỏi giải thích nguyên nhân mà không nhắc lại mã
    res2 = run_chat_graph(
        "Tại sao nó lại giảm?",
        price_source=real_deps.price_source,
        news_source=real_deps.news_source,
        history_store=real_deps.history_store,
        memory_store=real_deps.memory_store,
        rewrite_brain=HeuristicRewriteBrain(),
        supervisor_brain=HeuristicSupervisorBrain(),
        user_id="user_flow",
        turn="turn_2",
    )
    assert res2.rewritten.symbol == "FPT"
    assert "FPT" in res2.rewritten.rewritten


# ==============================================================================
# 2. Long-Term Memory Tests (Facts, Isolation, Vector Fallback)
# ==============================================================================

def test_long_term_fallback_save_and_recall():
    """Kiểm tra lưu trữ và truy hồi fact dài hạn khi Qdrant không khả dụng (in-memory fallback)."""
    uid = "test_user_ltm"
    turn = "ltm_turn_1"
    store_memory(
        {
            "user_id": uid,
            "question": "Tôi thích đầu tư mã VNM dài hạn",
            "answer": "Ghi nhận bạn quan tâm đến VNM.",
            "symbols": ["VNM"],
            "rewritten_question": "Tôi thích đầu tư mã VNM",
            "turn": turn,
        }
    )

    recalled = recall_memory({"user_id": uid, "question": "Danh mục của tôi có gì?", "turn": turn})
    assert isinstance(recalled.get("memories"), list)


def test_long_term_user_isolation():
    """Đảm bảo ký ức của User A không bao giờ bị rò rỉ sang User B."""
    store_memory({"user_id": "user_A", "question": "Mã bí mật của tôi là FPT", "answer": "OK", "symbols": ["FPT"]})
    res_b = recall_memory({"user_id": "user_B", "question": "Mã bí mật của tôi là gì?"})
    memories_b = res_b.get("memories") or []
    assert not any("FPT" in m for m in memories_b)


# ==============================================================================
# 3. Session & Message Database Persistence Tests
# ==============================================================================

def test_session_and_message_crud(tmp_path):
    """Kiểm tra tạo, đọc, cập nhật và xóa phiên hội thoại (cascade xóa tin nhắn)."""
    db_file = tmp_path / "test_session_crud.db"
    conn = get_connection(str(db_file))
    init_db(conn)

    s_repo = SessionRepository(conn)
    m_repo = MessageRepository(conn)

    # 1. Tạo session
    session = s_repo.create(title="Phiên phân tích FPT")
    assert session.id is not None
    assert session.title == "Phiên phân tích FPT"

    # 2. Tạo tin nhắn
    msg1 = m_repo.create(session_id=session.id, role="user", content="Giá FPT?")
    msg2 = m_repo.create(session_id=session.id, role="assistant", content="Giá FPT là 125.0.")

    messages = m_repo.list_by_session(session.id)
    assert len(messages) == 2
    assert messages[0].content == "Giá FPT?"

    # 3. Cập nhật tiêu đề session
    s_repo.update_title(session.id, "Phiên phân tích chuyên sâu FPT")
    updated_session = s_repo.get(session.id)
    assert updated_session.title == "Phiên phân tích chuyên sâu FPT"

    # 4. Xóa session (cascade xóa tin nhắn)
    deleted = s_repo.delete(session.id)
    assert deleted is True
    assert s_repo.get(session.id) is None
    assert len(m_repo.list_by_session(session.id)) == 0

    conn.close()


def test_chat_creates_session_if_none_and_auto_titles(client: TestClient, monkeypatch):
    """Kiểm tra gọi POST /api/v1/chat khi chưa có session_id sẽ tự động tạo session và đặt tiêu đề."""
    monkeypatch.setattr(
        "backend.main.ai_chat",
        lambda question, user_id, request_id: {
            "answer": "HPG là mã thép đầu ngành tại Việt Nam.",
            "route": "normal",
            "steps": [{"name": "price_agent", "status": "done"}],
        },
    )

    resp = client.post("/api/v1/chat", json={"question": "Phân tích mã cổ phiếu HPG"})
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    assert "message_id" in data
    session_id = data["session_id"]

    res_get = client.get(f"/api/v1/sessions/{session_id}")
    assert res_get.status_code == 200
    detail = res_get.json()
    assert "HPG" in detail["session"]["title"]
    assert detail["message_count"] == 2
