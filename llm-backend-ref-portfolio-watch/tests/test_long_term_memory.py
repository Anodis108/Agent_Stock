"""Tests for Phase 8 — Long-term memory, Qdrant optional & in-memory fallback."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.portfolio_watch.agents.answer_composer import AnswerComposeResult
from src.portfolio_watch.agents.supervisor_agent import (
    HeuristicRewriteBrain,
    recall_memory,
    rewrite_question,
    store_memory,
)
from src.portfolio_watch.application.answer_question import answer_question
from src.portfolio_watch.domain.ports import PriceBar, PriceQuote
from src.portfolio_watch.graph.chat import run_chat_graph
from src.portfolio_watch.infra.storage.long_term_memory import (
    clear_long_term_fallback,
    recall_long_term,
    save_to_long_term,
)
from src.portfolio_watch.infra.storage.memory_store import SqliteMemoryStore
from src.portfolio_watch.shared.schemas import MemoryFact, parse_memory_fact
from src.portfolio_watch.shared.settings import Settings, settings

ROOT = Path(__file__).resolve().parents[1]


class DummyPriceSource:
    def fetch_latest_close(self, symbol: str) -> PriceQuote:
        return PriceQuote(symbol=symbol, latest_close=120.0, prev_close=118.0)


class DummyNewsSource:
    def fetch_news(self, symbol: str, query: str | None = None, *, days: int | None = None) -> list:
        return []


class DummyHistoryStore:
    def read_history(self, symbol: str, days: int = 30) -> list[PriceBar]:
        return []


class DummyAnswerBrain:
    def compose(self, **kwargs) -> AnswerComposeResult:
        sym = kwargs.get("symbol") or "N/A"
        return AnswerComposeResult(answer=f"Cổ phiếu {sym} có giá đóng cửa 120.0.")


@pytest.fixture(autouse=True)
def _clean_memory():
    """Reset long-term fallback store before and after each test."""
    clear_long_term_fallback()
    yield
    clear_long_term_fallback()


# ─── 1. Settings & .env.example ───────────────────────────────────────────────

def test_settings_qdrant_defaults_and_env_override(monkeypatch):
    assert settings.qdrant_url is None or isinstance(settings.qdrant_url, str)
    assert settings.qdrant_collection == "portfolio_watch_memory"
    assert settings.embedding_dim == 1536

    monkeypatch.setenv("QDRANT_URL", "http://test-qdrant:6333")
    monkeypatch.setenv("QDRANT_API_KEY", "test-key")
    monkeypatch.setenv("QDRANT_COLLECTION", "custom_collection")
    custom = Settings()
    assert custom.qdrant_url == "http://test-qdrant:6333"
    assert custom.qdrant_api_key == "test-key"
    assert custom.qdrant_collection == "custom_collection"


def test_env_example_has_qdrant_vars():
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "QDRANT_URL" in text
    assert "QDRANT_API_KEY" in text
    assert "QDRANT_COLLECTION" in text
    assert "EMBEDDING_MODEL" in text
    assert "EMBEDDING_DIM" in text


# ─── 2. Schema MemoryFact ─────────────────────────────────────────────────────

def test_memory_fact_schema_and_parser():
    mf = parse_memory_fact({"worth_saving": True, "fact": "User quan tâm FPT"})
    assert mf.worth_saving is True
    assert mf.fact == "User quan tâm FPT"

    # Boolean string conversion
    mf2 = parse_memory_fact({"worth_saving": "yes", "fact": "Thích đầu tư dài hạn"})
    assert mf2.worth_saving is True

    # Empty / none fact
    mf3 = parse_memory_fact({"worth_saving": True, "fact": "none"})
    assert mf3.fact == ""

    # Invalid input fallback
    mf4 = parse_memory_fact("invalid json")
    assert mf4.worth_saving is False
    assert mf4.fact == ""


# ─── 3. In-memory Fallback (Save & Recall) ─────────────────────────────────────

def test_long_term_fallback_save_and_recall():
    save_to_long_term("user_1", "Người dùng theo dõi dài hạn mã FPT")
    save_to_long_term("user_1", "Người dùng có khẩu vị rủi ro thấp và nắm giữ VNM")

    # Recall theo keyword match
    results_fpt = recall_long_term("user_1", "cổ phiếu FPT thế nào", k=2)
    assert len(results_fpt) >= 1
    assert "FPT" in results_fpt[0]

    # Recall top-k
    results_all = recall_long_term("user_1", "danh mục đầu tư", k=1)
    assert len(results_all) == 1


def test_long_term_user_isolation():
    save_to_long_term("user_alice", "Alice quan tâm FPT")
    save_to_long_term("user_bob", "Bob quan tâm HPG")

    alice_mem = recall_long_term("user_alice", "cổ phiếu quan tâm")
    bob_mem = recall_long_term("user_bob", "cổ phiếu quan tâm")

    assert any("FPT" in m for m in alice_mem)
    assert not any("HPG" in m for m in alice_mem)

    assert any("HPG" in m for m in bob_mem)
    assert not any("FPT" in m for m in bob_mem)


# ─── 4. Empty / None user_id Handling ─────────────────────────────────────────

@pytest.mark.parametrize("empty_user", [None, "", "   "])
def test_long_term_no_user_id_skips_without_crash(empty_user):
    # save không crash
    save_to_long_term(empty_user, "Fact should not be saved")
    # recall trả về rỗng không crash
    recalled = recall_long_term(empty_user, "query")
    assert recalled == []

    # recall_memory node helper không crash
    rec_res = recall_memory({"user_id": empty_user, "question": "Hỏi giá"})
    assert rec_res == {"memories": []}

    # store_memory node helper không crash
    store_res = store_memory(
        {"user_id": empty_user, "question": "Hỏi giá", "answer": "120k"}
    )
    assert store_res == {}


def test_store_memory_empty_question_or_answer_skips():
    assert store_memory({"user_id": "u1", "question": "", "answer": "120k"}) == {}
    assert store_memory({"user_id": "u1", "question": "Hỏi", "answer": ""}) == {}


# ─── 5. Qdrant Error Fallback to In-Memory ────────────────────────────────────

def test_qdrant_unreachable_falls_back_to_in_memory():
    mock_client = MagicMock()
    mock_client.collection_exists.side_effect = ConnectionError("Qdrant unreachable")

    # Save khi Qdrant ném lỗi -> tự động fallback in-memory, không raise
    save_to_long_term("u_fallback", "User quan tâm HPG", client=mock_client)

    # Recall khi Qdrant ném lỗi -> tự động fallback in-memory
    mock_client.query_points.side_effect = ConnectionError("Qdrant unreachable")
    memories = recall_long_term("u_fallback", "HPG", client=mock_client)
    assert len(memories) >= 1
    assert "HPG" in memories[0]


def test_qdrant_vector_store_when_mock_embed_available():
    """Kiểm tra đường code Qdrant khi có Qdrant client và embed_fn."""
    from qdrant_client import QdrantClient

    client = QdrantClient(location=":memory:")

    def mock_embed(texts: list[str]) -> list[list[float]]:
        # Giả lập vector 4 chiều đơn giản
        return [[1.0, 0.0, 0.0, 0.0] for _ in texts]

    def mock_embed_query(q: str) -> list[float]:
        return [1.0, 0.0, 0.0, 0.0]

    save_to_long_term(
        "u_qdrant",
        "Fact qua Qdrant vector",
        client=client,
        embed_fn=mock_embed,
    )

    results = recall_long_term(
        "u_qdrant",
        "Fact",
        k=2,
        client=client,
        embed_fn=mock_embed_query,
    )
    assert len(results) >= 1
    assert "Fact qua Qdrant vector" in results[0]


# ─── 6. Rewrite Question Integrates Long-term Memory ──────────────────────────

def test_rewrite_question_resolves_symbol_from_long_term_memories():
    # Câu hỏi follow-up dùng đại từ "mã đó", conversation rỗng, nhưng memories có FPT
    memories = ["Người dùng quan tâm theo dõi mã FPT."]
    rewritten = rewrite_question(
        "Mã đó hôm nay giá thế nào?",
        conversation=[],
        brain=HeuristicRewriteBrain(),
        memories=memories,
    )
    assert rewritten.symbol == "FPT"
    assert "FPT" in rewritten.rewritten


# ─── 7. run_chat_graph Integration (With & Without user_id) ──────────────────

def test_run_chat_graph_stores_and_recalls_long_term_memory(tmp_path):
    db_path = tmp_path / "test_long_term.db"
    mem_store = SqliteMemoryStore(db_path)
    price_src = DummyPriceSource()
    news_src = DummyNewsSource()
    hist_src = DummyHistoryStore()
    ans_brain = DummyAnswerBrain()

    user_id = "user_investor_01"

    # Turn 1: User hỏi có nhắc FPT -> store_memory tự trích xuất fact lưu vào long-term
    res1 = run_chat_graph(
        "Tôi đang theo dõi cổ phiếu FPT",
        price_source=price_src,
        news_source=news_src,
        history_store=hist_src,
        memory_store=mem_store,
        user_id=user_id,
        answer_brain=ans_brain,
        turn="t1",
    )
    assert res1.rewritten.symbol == "FPT"

    # Kiểm tra long-term memory đã có fact cho user_id
    stored_facts = recall_long_term(user_id, "FPT")
    assert len(stored_facts) >= 1
    assert "FPT" in stored_facts[0]

    # Turn 2: User mới mở session mới (dùng memory_store rỗng / session khác)
    # nhưng CÙNG user_id -> recall_memory đọc fact từ long-term
    clean_store = SqliteMemoryStore(tmp_path / "new_session.db")
    res2 = run_chat_graph(
        "Mã đó hôm nay giá thế nào?",
        price_source=price_src,
        news_source=news_src,
        history_store=hist_src,
        memory_store=clean_store,
        user_id=user_id,
        answer_brain=ans_brain,
        turn="t2",
    )
    # Long-term recall trả về FPT và rewrite_question giải quyết được mã FPT
    assert res2.rewritten.symbol == "FPT"
    assert len(res2.memories) >= 1
    assert "FPT" in res2.memories[0]


def test_run_chat_graph_without_user_id_skips_long_term_no_crash(tmp_path):
    db_path = tmp_path / "test_no_user.db"
    mem_store = SqliteMemoryStore(db_path)
    price_src = DummyPriceSource()
    news_src = DummyNewsSource()
    hist_src = DummyHistoryStore()
    ans_brain = DummyAnswerBrain()

    # Chạy với user_id=None
    res_none = run_chat_graph(
        "Giá FPT hôm nay?",
        price_source=price_src,
        news_source=news_src,
        history_store=hist_src,
        memory_store=mem_store,
        user_id=None,
        answer_brain=ans_brain,
        turn="t_none",
    )
    assert res_none.answer
    assert res_none.memories == []

    # Chạy với user_id=""
    res_blank = run_chat_graph(
        "Giá FPT hôm nay?",
        price_source=price_src,
        news_source=news_src,
        history_store=hist_src,
        memory_store=mem_store,
        user_id="",
        answer_brain=ans_brain,
        turn="t_blank",
    )
    assert res_blank.answer
    assert res_blank.memories == []


def test_answer_question_passes_user_id_and_returns_memories(tmp_path):
    db_path = tmp_path / "test_app.db"
    mem_store = SqliteMemoryStore(db_path)
    price_src = DummyPriceSource()
    news_src = DummyNewsSource()
    hist_src = DummyHistoryStore()
    ans_brain = DummyAnswerBrain()

    save_to_long_term("user_app", "Khách hàng theo dõi FPT")

    result = answer_question(
        "FPT giá sao rồi?",
        price_source=price_src,
        news_source=news_src,
        history_store=hist_src,
        memory_store=mem_store,
        user_id="user_app",
        answer_brain=ans_brain,
    )
    assert result.answer
    assert len(result.memories) >= 1
    assert "FPT" in result.memories[0]
