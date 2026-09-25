"""Tests for Phase 7 — Short-term conversation memory, sliding window & TTL freshness."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from backend.agents.answer_composer import AnswerComposeResult
from backend.agents.supervisor_agent import (
    HeuristicRewriteBrain,
    HeuristicSupervisorBrain,
)
from backend.domain.entities import RoutingDecision
from backend.domain.ports import PriceBar, PriceQuote
from backend.graph.chat import run_chat_graph
from backend.infra.storage.memory_store import (
    SqliteMemoryStore,
    filter_conversation_history,
    parse_timestamp,
)
from backend.shared.settings import Settings, settings

ROOT = Path(__file__).resolve().parents[1]


class DummyPriceSource:
    def __init__(self, quote: PriceQuote | None = None):
        self._quote = quote or PriceQuote(symbol="FPT", latest_close=100.0, prev_close=98.0)

    def fetch_latest_close(self, symbol: str) -> PriceQuote:
        return PriceQuote(symbol=symbol, latest_close=100.0, prev_close=98.0)


class DummyNewsSource:
    def fetch_news(self, symbol: str, query: str | None = None, *, days: int | None = None) -> list:
        return []


class DummyHistoryStore:
    def read_history(self, symbol: str, days: int = 30) -> list[PriceBar]:
        return []


class DummyAnswerBrain:
    def compose(self, **kwargs) -> AnswerComposeResult:
        sym = kwargs.get("symbol") or "N/A"
        return AnswerComposeResult(answer=f"Thông tin giá cho mã {sym}.")


# ─── 1. Settings & .env.example ───────────────────────────────────────────────

def test_settings_memory_defaults_and_env_override(monkeypatch):
    assert settings.memory_short_term_window == 20
    assert settings.memory_short_term_ttl_minutes == 60

    monkeypatch.setenv("MEMORY_SHORT_TERM_WINDOW", "15")
    monkeypatch.setenv("MEMORY_SHORT_TERM_TTL_MINUTES", "30")
    custom = Settings()
    assert custom.memory_short_term_window == 15
    assert custom.memory_short_term_ttl_minutes == 30


def test_env_example_has_memory_vars():
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "MEMORY_SHORT_TERM_WINDOW" in text
    assert "MEMORY_SHORT_TERM_TTL_MINUTES" in text


# ─── 2. Timestamp Parsing & Filtering ────────────────────────────────────────

def test_parse_timestamp_formats():
    assert parse_timestamp(None) is None
    assert parse_timestamp("") is None

    # SQLite datetime('now') format
    dt_sqlite = parse_timestamp("2026-09-22 01:00:00")
    assert dt_sqlite is not None
    assert dt_sqlite.tzinfo == timezone.utc
    assert dt_sqlite.hour == 1

    # ISO with Z
    dt_iso_z = parse_timestamp("2026-09-22T01:00:00Z")
    assert dt_iso_z is not None
    assert dt_iso_z.tzinfo == timezone.utc

    # ISO with timezone offset
    dt_offset = parse_timestamp("2026-09-22T08:00:00+07:00")
    assert dt_offset is not None
    assert dt_offset.astimezone(timezone.utc) == dt_sqlite

    # Datetime object
    now = datetime.now(timezone.utc)
    assert parse_timestamp(now) == now

    # Unix timestamp
    ts = 1700000000
    assert parse_timestamp(ts) == datetime.fromtimestamp(ts, tz=timezone.utc)


def test_filter_conversation_history_sliding_window():
    items = [
        {"role": "user", "content": f"msg {i}", "created_at": None}
        for i in range(10)
    ]
    # Sliding window = 3
    filtered = filter_conversation_history(items, limit=3, ttl_minutes=0)
    assert len(filtered) == 3
    assert [m["content"] for m in filtered] == ["msg 7", "msg 8", "msg 9"]

    # Limit larger than total items
    filtered_all = filter_conversation_history(items, limit=20, ttl_minutes=0)
    assert len(filtered_all) == 10


def test_filter_conversation_history_ttl_expiry():
    now = datetime.now(timezone.utc)
    t_old = (now - timedelta(minutes=120)).strftime("%Y-%m-%d %H:%M:%S")
    t_fresh1 = (now - timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
    t_fresh2 = (now - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")

    items = [
        {"role": "user", "content": "cũ 120m", "created_at": t_old},
        {"role": "user", "content": "mới 30m", "created_at": t_fresh1},
        {"role": "user", "content": "mới 5m", "created_at": t_fresh2},
        {"role": "assistant", "content": "no-timestamp", "created_at": None},
    ]

    # TTL 60m: t_old (120m) bị drop; t_fresh1 (30m), t_fresh2 (5m) và no-timestamp được giữ
    filtered = filter_conversation_history(items, limit=10, ttl_minutes=60, now=now)
    contents = [m["content"] for m in filtered]
    assert "cũ 120m" not in contents
    assert "mới 30m" in contents
    assert "mới 5m" in contents
    assert "no-timestamp" in contents

    # Tất cả hết hạn
    only_old = [{"role": "user", "content": "cũ", "created_at": t_old}]
    assert filter_conversation_history(only_old, limit=10, ttl_minutes=60, now=now) == []


# ─── 3. SqliteMemoryStore Integration ────────────────────────────────────────

def test_sqlite_memory_store_window_and_ttl(tmp_path):
    db = str(tmp_path / "test_mem.db")
    store = SqliteMemoryStore(db)

    now = datetime.now(timezone.utc)
    t_old = now - timedelta(minutes=90)
    t_fresh = now - timedelta(minutes=10)

    # Thêm tin nhắn cũ (hết hạn TTL 60m)
    store.append_conversation("u1", "user", "Giá HPG?", created_at=t_old)
    store.append_conversation("u1", "assistant", "HPG giá 28.", created_at=t_old)

    # Thêm tin nhắn mới (trong window và TTL)
    store.append_conversation("u1", "user", "Giá FPT?", created_at=t_fresh)
    store.append_conversation("u1", "assistant", "FPT giá 130.", created_at=t_fresh)

    # Đọc mặc định (TTL = 60m): 2 tin nhắn HPG bị loại bỏ, chỉ còn 2 tin FPT
    conv = store.list_conversation("u1", limit=10, ttl_minutes=60, now=now)
    assert len(conv) == 2
    assert conv[0]["content"] == "Giá FPT?"
    assert conv[1]["content"] == "FPT giá 130."

    # Tắt TTL (ttl_minutes=0): đọc đủ cả 4 tin
    conv_all = store.list_conversation("u1", limit=10, ttl_minutes=0)
    assert len(conv_all) == 4
    assert conv_all[0]["content"] == "Giá HPG?"

    # Sliding window: giới hạn lấy 1 tin mới nhất
    conv_1 = store.list_conversation("u1", limit=1, ttl_minutes=60, now=now)
    assert len(conv_1) == 1
    assert conv_1[0]["content"] == "FPT giá 130."


# ─── 4. Follow-up Rewrite & Context Resolution ───────────────────────────────

def test_followup_resolves_symbol_in_window():
    brain = HeuristicRewriteBrain()
    conversation = [
        {"role": "user", "content": "Giá cổ phiếu FPT hiện tại ra sao?"},
        {"role": "assistant", "content": "FPT đang có giá 130.0, tăng +2.5%."},
    ]

    # Follow-up 1: "giá hôm nay thế nào?" (không có ticker trực tiếp)
    q1 = "giá hôm nay thế nào?"
    res1 = brain.rewrite(q1, conversation)
    assert res1.symbol == "FPT"
    assert "FPT" in res1.symbols
    assert "[FPT]" in res1.rewritten

    # Follow-up 2: dùng đại từ "mã đó sao rồi?"
    q2 = "mã đó sao rồi?"
    res2 = brain.rewrite(q2, conversation)
    assert res2.symbol == "FPT"
    assert "[FPT]" in res2.rewritten

    # Follow-up 3: "thế còn tin tức sao rồi?"
    q3 = "thế còn tin tức sao rồi?"
    res3 = brain.rewrite(q3, conversation)
    assert res3.symbol == "FPT"
    assert res3.intent == "news_lookup"


def test_expired_conversation_does_not_resolve_symbol():
    brain = HeuristicRewriteBrain()
    # Khi phiên trước đã hết hạn, conversation truyền vào là rỗng
    empty_conversation = []

    res = brain.rewrite("giá hôm nay thế nào?", empty_conversation)
    assert res.symbol is None
    assert res.symbols == []
    assert "[FPT]" not in res.rewritten


# ─── 5. End-to-End Chat Graph with Short-term Window & TTL ───────────────────

def test_run_chat_graph_followup_resolves_ticker_in_session(tmp_path):
    db = str(tmp_path / "test_chat.db")
    store = SqliteMemoryStore(db)
    price_src = DummyPriceSource()
    news_src = DummyNewsSource()
    hist_store = DummyHistoryStore()
    rewrite_brain = HeuristicRewriteBrain()
    sup_brain = HeuristicSupervisorBrain()
    ans_brain = DummyAnswerBrain()

    # Lần 1: User hỏi FPT
    res1 = run_chat_graph(
        "Giá FPT hiện tại?",
        price_source=price_src,
        news_source=news_src,
        history_store=hist_store,
        memory_store=store,
        user_id="test_user",
        rewrite_brain=rewrite_brain,
        supervisor_brain=sup_brain,
        answer_brain=ans_brain,
    )
    assert res1.rewritten.symbol == "FPT"
    assert "FPT" in (res1.answer or "")

    # Lần 2: Follow-up không có ticker "giá hôm nay thế nào?"
    res2 = run_chat_graph(
        "giá hôm nay thế nào?",
        price_source=price_src,
        news_source=news_src,
        history_store=hist_store,
        memory_store=store,
        user_id="test_user",
        rewrite_brain=rewrite_brain,
        supervisor_brain=sup_brain,
        answer_brain=ans_brain,
    )
    # Tự động nhớ FPT từ conversation memory trong sliding window
    assert res2.rewritten.symbol == "FPT"
    assert "FPT" in res2.rewritten.rewritten


def test_run_chat_graph_expired_ttl_drops_symbol(tmp_path):
    db = str(tmp_path / "test_chat_ttl.db")
    store = SqliteMemoryStore(db)
    price_src = DummyPriceSource()
    news_src = DummyNewsSource()
    hist_store = DummyHistoryStore()
    rewrite_brain = HeuristicRewriteBrain()
    sup_brain = HeuristicSupervisorBrain()
    ans_brain = DummyAnswerBrain()

    # Thêm turn cũ cách đây 2 giờ (hết hạn TTL 60m)
    now = datetime.now(timezone.utc)
    t_old = now - timedelta(minutes=120)
    store.append_conversation("user_ttl", "user", "Giá HPG?", created_at=t_old)
    store.append_conversation("user_ttl", "assistant", "HPG giá 28.", created_at=t_old)

    # Hỏi câu follow-up không có ticker khi phiên cũ đã hết hạn TTL
    res = run_chat_graph(
        "giá hôm nay thế nào?",
        price_source=price_src,
        news_source=news_src,
        history_store=hist_store,
        memory_store=store,
        user_id="user_ttl",
        rewrite_brain=rewrite_brain,
        supervisor_brain=sup_brain,
        answer_brain=ans_brain,
        ttl_minutes=60,
    )
    # Vì tin nhắn cũ > 60m đã bị drop, supervisor/rewrite không còn nhận diện HPG
    assert res.rewritten.symbol is None


def test_run_chat_graph_respects_sliding_window_limit(tmp_path):
    db = str(tmp_path / "test_chat_window.db")
    store = SqliteMemoryStore(db)
    price_src = DummyPriceSource()
    news_src = DummyNewsSource()
    hist_store = DummyHistoryStore()
    rewrite_brain = HeuristicRewriteBrain()
    sup_brain = HeuristicSupervisorBrain()
    ans_brain = DummyAnswerBrain()

    # User chat 6 tin nhắn
    for i, sym in enumerate(["HPG", "VNM", "SSI"]):
        store.append_conversation("u_win", "user", f"Giá {sym}?")
        store.append_conversation("u_win", "assistant", f"{sym} giá 50.")

    # Với limit=2 (chỉ lấy 2 tin nhắn gần nhất: user hỏi SSI, assistant trả lời SSI)
    res = run_chat_graph(
        "nó thế nào rồi?",
        price_source=price_src,
        news_source=news_src,
        history_store=hist_store,
        memory_store=store,
        user_id="u_win",
        rewrite_brain=rewrite_brain,
        supervisor_brain=sup_brain,
        answer_brain=ans_brain,
        limit=2,
    )
    # Ticker gần nhất trong window là SSI
    assert res.rewritten.symbol == "SSI"


# ─── 6. Turn 1 ➔ Turn 2 Multi-Turn Follow-up ("Tại sao lại giảm?") ─────────

def test_followup_explain_why_resolves_symbol_and_intent():
    """Kiểm tra câu hỏi nối tiếp 'Tại sao lại giảm?' kế thừa đúng mã FPT và intent explain."""
    brain = HeuristicRewriteBrain()
    conversation = [
        {"role": "user", "content": "FPT tăng hay giảm hôm nay?"},
        {"role": "assistant", "content": "Hôm nay cổ phiếu FPT giảm 1.5% do áp lực bán phiên chiều."},
    ]

    # Turn 2: Câu hỏi nguyên nhân không có ticker
    res_down = brain.rewrite("Tại sao lại giảm?", conversation)
    assert res_down.symbol == "FPT"
    assert res_down.symbols == ["FPT"]
    assert res_down.intent == "explain"
    assert res_down.rewritten == "Tại sao giá cổ phiếu FPT lại giảm hôm nay?"

    # Kiểm tra trường hợp hỏi 'Tại sao lại tăng?'
    res_up = brain.rewrite("Tại sao lại tăng?", conversation)
    assert res_up.symbol == "FPT"
    assert res_up.symbols == ["FPT"]
    assert res_up.intent == "explain"
    assert res_up.rewritten == "Tại sao giá cổ phiếu FPT lại tăng hôm nay?"


def test_run_chat_graph_turn1_turn2_explain_flow(tmp_path):
    """End-to-End Chat Graph: Turn 1 (FPT tăng hay giảm) -> Turn 2 (Tại sao lại giảm?) -> Turn 3 (Còn tin tức gì không?)."""
    db = str(tmp_path / "test_turn1_turn2.db")
    store = SqliteMemoryStore(db)
    price_src = DummyPriceSource()
    news_src = DummyNewsSource()
    hist_store = DummyHistoryStore()
    rewrite_brain = HeuristicRewriteBrain()
    sup_brain = HeuristicSupervisorBrain()
    ans_brain = DummyAnswerBrain()

    user_id = "user_multiturn_flow"

    # Turn 1: Người dùng hỏi trạng thái giá FPT
    res1 = run_chat_graph(
        "FPT tăng hay giảm hôm nay?",
        price_source=price_src,
        news_source=news_src,
        history_store=hist_store,
        memory_store=store,
        user_id=user_id,
        rewrite_brain=rewrite_brain,
        supervisor_brain=sup_brain,
        answer_brain=ans_brain,
    )
    assert res1.rewritten.symbol == "FPT"
    assert "FPT" in (res1.answer or "")

    # Turn 2: Người dùng hỏi tiếp nguyên nhân 'Tại sao lại giảm?'
    res2 = run_chat_graph(
        "Tại sao lại giảm?",
        price_source=price_src,
        news_source=news_src,
        history_store=hist_store,
        memory_store=store,
        user_id=user_id,
        rewrite_brain=rewrite_brain,
        supervisor_brain=sup_brain,
        answer_brain=ans_brain,
    )
    # Kế thừa chính xác mã FPT từ Turn 1
    assert res2.rewritten.symbol == "FPT"
    assert res2.rewritten.symbols == ["FPT"]
    assert res2.rewritten.intent == "explain"
    assert res2.rewritten.rewritten == "Tại sao giá cổ phiếu FPT lại giảm hôm nay?"
    # Supervisor phân bổ sang Price, News và Eval để phân tích nguyên nhân
    assert res2.routing.route == "explain"
    assert set(res2.routing.agents_to_call) == {"price", "news", "eval"}
    assert "FPT" in (res2.answer or "")

    # Turn 3: Người dùng hỏi tiếp tin tức mà không cần nhắc lại ticker
    res3 = run_chat_graph(
        "Còn tin tức gì nữa không?",
        price_source=price_src,
        news_source=news_src,
        history_store=hist_store,
        memory_store=store,
        user_id=user_id,
        rewrite_brain=rewrite_brain,
        supervisor_brain=sup_brain,
        answer_brain=ans_brain,
    )
    assert res3.rewritten.symbol == "FPT"
    assert res3.rewritten.intent == "news_lookup"
    assert set(res3.routing.agents_to_call) == {"price", "news"}
    assert "FPT" in (res3.answer or "")

