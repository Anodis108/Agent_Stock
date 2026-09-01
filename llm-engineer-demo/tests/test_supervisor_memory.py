"""Short-term (thread_id / history) + long-term (user_id / Qdrant) cho agent_pr.

Không gọi OpenAI / vnstock: mock recall/store và mini-graph checkpointer.
"""

from __future__ import annotations

from typing import Annotated, TypedDict

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from pydantic import ValidationError

from app.agent_pr.craw_agent.schemas import Agent_Output as PriceOut
from app.agent_pr.news_agent.schemas import Agent_Output as NewsOut
from app.agent_pr.supervisor_agent.nodes import (
    _coordinate,
    _gather_stuck,
    _pending_gather,
    recall_memory,
    rewrite_question,
    store_memory,
)
from app.agent_pr.supervisor_agent.schemas import AgentPlan, Agent_Input
from app.agent_pr.supervisor_agent.state import _append_trim


def test_append_trim_giu_cua_so():
    left = [{"i": i} for i in range(18)]
    right = [{"i": 18}, {"i": 19}, {"i": 20}]
    out = _append_trim(left, right)
    assert len(out) == 20
    assert out[0]["i"] == 1
    assert out[-1]["i"] == 20


def test_pending_gather_doi_ma_phai_fetch_lai():
    plan = AgentPlan(
        symbol="FPT",
        use_price=True,
        use_news=True,
        use_db=False,
        use_eval=False,
        use_synth=True,
        reasoning="đổi mã",
    )
    state = {
        "price": PriceOut(symbol="HPG", last=22100),
        "news": NewsOut(symbol="HPG", articles=[]),
    }
    assert _pending_gather(state, plan) == ["price_agent", "news_agent"]


def test_pending_gather_cung_ma_tai_dung_gia():
    plan = AgentPlan(
        symbol="HPG",
        use_price=True,
        use_news=True,
        use_db=False,
        use_eval=False,
        use_synth=True,
        reasoning="cùng mã",
    )
    state = {
        "price": PriceOut(symbol="HPG", last=22100, pct_change=0.5),
        "news": NewsOut(symbol="HPG", articles=[]),
    }
    assert _pending_gather(state, plan) == []


def test_pending_gather_gia_da_crawl_loi_thi_khong_fetch_lai():
    """last=0 sau khi đã crawl (cùng symbol) = đã thử và thất bại (mã sai /
    vnstock lỗi) — KHÔNG retry vô hạn (từng gây crash recursion_limit khi
    hỏi mã không tồn tại). Khác _pending_gather (chưa thử): xem _gather_stuck."""
    plan = AgentPlan(
        symbol="HPG",
        use_price=True,
        use_news=False,
        use_db=False,
        use_eval=False,
        use_synth=True,
        reasoning="giá lỗi",
    )
    state = {"price": PriceOut(symbol="HPG", last=0, source="Lỗi vnstock HPG: Invalid symbol")}
    assert _pending_gather(state, plan) == []
    assert _gather_stuck(state, plan) == ["price_agent"]


def test_pending_gather_chua_crawl_thi_fetch():
    """Chưa có price nào trong state (khác symbol/None) — vẫn phải gather bình thường."""
    plan = AgentPlan(
        symbol="HPG",
        use_price=True,
        use_news=False,
        use_db=False,
        use_eval=False,
        use_synth=True,
        reasoning="chưa crawl",
    )
    assert _pending_gather({}, plan) == ["price_agent"]
    assert _gather_stuck({}, plan) == []


def test_pending_gather_db_khong_nam_trong_crawl():
    plan = AgentPlan(
        symbol="FPT",
        use_price=False,
        use_news=True,
        use_db=True,
        use_eval=False,
        use_synth=True,
        reasoning="ghi tin",
    )
    assert _pending_gather({"turn": "t1"}, plan) == ["news_agent"]


def test_pending_gather_sau_khi_co_news_khong_goi_db():
    plan = AgentPlan(
        symbol="FPT",
        use_price=False,
        use_news=True,
        use_db=True,
        use_eval=False,
        use_synth=True,
        reasoning="ghi tin",
    )
    state = {
        "turn": "t1",
        "news": NewsOut(
            symbol="FPT",
            articles=[],
        ),
    }
    assert _pending_gather(state, plan) == []


def test_route_lookup_db_truoc():
    from langgraph.types import Send

    from app.agent_pr.supervisor_agent.nodes import route_coordinator

    plan = AgentPlan(
        symbol="FPT",
        use_price=False,
        use_news=True,
        use_db=True,
        use_eval=False,
        use_synth=True,
        reasoning="ghi tin",
    )
    sends = route_coordinator(
        {
            "next_wave": "db_lookup",
            "symbol": "FPT",
            "turn": "t1",
            "plan": plan,
        }
    )
    assert isinstance(sends, list) and len(sends) == 1
    assert isinstance(sends[0], Send)
    assert sends[0].node == "db_agent"
    assert sends[0].arg["mode"] == "read"
    assert sends[0].arg["candidate_news"] == []
    assert "_trace_span" not in sends[0].arg


def test_route_db_write_kem_candidate_sau_news():
    from langgraph.types import Send

    from app.agent_pr.news_agent.schemas import NewsItem
    from app.agent_pr.supervisor_agent.nodes import route_coordinator

    plan = AgentPlan(
        symbol="FPT",
        use_price=False,
        use_news=True,
        use_db=True,
        use_eval=False,
        use_synth=True,
        reasoning="ghi tin",
    )
    state = {
        "next_wave": "db_write",
        "symbol": "FPT",
        "turn": "t1",
        "plan": plan,
        "news": NewsOut(
            symbol="FPT",
            articles=[NewsItem(title="Tin A", url="https://cafef.vn/a.chn")],
        ),
    }
    sends = route_coordinator(state)
    assert isinstance(sends, list) and len(sends) == 1
    assert isinstance(sends[0], Send)
    assert sends[0].node == "db_agent"
    assert sends[0].arg["mode"] == "write"
    assert "_trace_span" not in sends[0].arg
    assert sends[0].arg["candidate_news"] == [
        {"title": "Tin A", "url": "https://cafef.vn/a.chn"}
    ]
    assert sends[0].arg["turn"] == "t1"


def test_route_hitl_toi_commit():
    from app.agent_pr.supervisor_agent.nodes import route_coordinator

    assert route_coordinator({"next_wave": "hitl"}) == "hitl_commit"


def test_hydrate_gia_tu_db():
    from app.agent_pr.db_agent.schemas import Agent_Output as DbOut
    from app.agent_pr.db_agent.schemas import PriceRow
    from app.agent_pr.supervisor_agent.nodes import _hydrate_from_db

    plan = AgentPlan(
        symbol="HPG",
        use_price=True,
        use_news=False,
        use_db=True,
        use_eval=False,
        use_synth=True,
        reasoning="đọc kho",
    )
    db = DbOut(
        symbol="HPG",
        price_history=[PriceRow(trading_date="20260828", close=22100)],
        detail="đọc",
    )
    extra = _hydrate_from_db({"db": db}, plan)
    assert extra["price"].source == "db"
    assert extra["price"].last == 22100
    assert extra["price"].pct_change is None
    assert "news" not in extra


def test_has_price_can_hai_phien():
    """1 hàng DB (không %) → vẫn hydrate last, nhưng chưa đủ để bỏ crawl."""
    from app.agent_pr.craw_agent.schemas import Agent_Output as PriceOut
    from app.agent_pr.supervisor_agent.nodes import _has_price

    one = PriceOut(symbol="HPG", last=22100, pct_change=None, source="db")
    assert not _has_price({"price": one}, "HPG")
    two = PriceOut(symbol="HPG", last=22100, pct_change=-1.2, source="db")
    assert _has_price({"price": two}, "HPG")


def test_recall_khong_user_van_ghi_history():
    out = recall_memory({"question": "giá HPG", "user_id": ""})
    assert out["memories"] == []
    assert out["history"] == [{"role": "user", "content": "giá HPG"}]


def test_coordinator_thieu_cau_khong_raise():
    out = _coordinate({"question": "", "symbol": "", "trace": []})
    assert out["next_wave"] == "done"
    assert "Lỗi" in out["draft"].answer


def test_rewrite_llm_viet_lai(monkeypatch):
    from app.agent_pr.supervisor_agent import nodes as n

    class _Parsed:
        query = "Giá và tin mới nhất của HPG?"
        symbol = "HPG"

    monkeypatch.setattr(
        n, "chat_parsed_with_usage", lambda *a, **k: (_Parsed(), {"prompt_tokens": 0, "completion_tokens": 0})
    )
    out = rewrite_question({"question": "HPG sao rồi", "trace": []})
    assert out["rewritten_question"] == "Giá và tin mới nhất của HPG?"
    assert out["symbol"] == "HPG"
    assert out["trace"][-1].startswith("Rewrite:")


def test_recall_dung_cau_rewrite(monkeypatch):
    from app.agent_pr.supervisor_agent import nodes as n

    seen: list[str] = []
    monkeypatch.setattr(
        n.memory,
        "recall_long_term",
        lambda uid, q, k=3: seen.append(q) or ["theo dõi HPG"],
    )
    out = recall_memory(
        {
            "question": "nó sao rồi",
            "rewritten_question": "Giá HPG hôm nay?",
            "user_id": "u1",
        }
    )
    assert seen == ["Giá HPG hôm nay?"]
    assert out["history"][0]["content"] == "nó sao rồi"


def test_recall_co_user(monkeypatch):
    from app.agent_pr.supervisor_agent import nodes as n

    monkeypatch.setattr(n.memory, "recall_long_term", lambda uid, q, k=3: ["theo dõi HPG"])
    out = recall_memory({"question": "tin mới?", "user_id": "u1"})
    assert out["memories"] == ["theo dõi HPG"]
    assert out["history"][0]["content"] == "tin mới?"


def test_store_bo_qua_khi_khong_user():
    assert store_memory({"user_id": "", "history": [{"role": "user", "content": "x"}]}) == {}


def test_store_luu_fact(monkeypatch):
    from app.agent_pr.supervisor_agent import nodes as n

    class _Parsed:
        worth_saving = True
        fact = "User theo dõi HPG."

    saved: list[tuple[str, str]] = []
    monkeypatch.setattr(
        n, "chat_parsed_with_usage", lambda *a, **k: (_Parsed(), {"prompt_tokens": 0, "completion_tokens": 0})
    )
    monkeypatch.setattr(
        n.memory, "save_to_long_term", lambda uid, fact: saved.append((uid, fact))
    )
    store_memory(
        {
            "user_id": "u1",
            "history": [
                {"role": "user", "content": "Tôi thích HPG"},
                {"role": "assistant", "content": "HPG giảm 1%."},
            ],
        }
    )
    assert saved == [("u1", "User theo dõi HPG.")]


def test_memory_fallback_tach_theo_user(monkeypatch):
    from app.agent_pr import memory as pr_memory

    monkeypatch.setattr(pr_memory, "_use_qdrant", lambda: False)
    pr_memory._FALLBACK.clear()
    pr_memory.save_to_long_term("alice", "theo dõi HPG")
    pr_memory.save_to_long_term("bob", "theo dõi FPT")
    assert "HPG" in " ".join(pr_memory.recall_long_term("alice", "cổ phiếu HPG"))
    assert all("HPG" not in f for f in pr_memory.recall_long_term("bob", "cổ phiếu HPG"))
    pr_memory.save_to_long_term("alice", "   ")
    assert len(pr_memory.recall_long_term("alice", "HPG")) == 1


def test_thread_id_bat_buoc():
    """Giống /assistant: thiếu hoặc chỉ khoảng trắng → không nhận request."""
    with pytest.raises(ValidationError):
        Agent_Input(symbol="HPG")
    from app.agent_pr.supervisor_agent.graph import run_supervisor

    with pytest.raises(ValueError, match="thread_id"):
        run_supervisor(Agent_Input(symbol="HPG", thread_id="   "))


def test_interrupt_before_hitl_commit_giong_m2():
    """Hub compile(interrupt_before=['hitl_commit']): dừng trước node, resume ainvoke(None)."""

    class Mini(TypedDict, total=False):
        staged: int
        committed: bool

    def stage(_state: Mini) -> dict:
        return {"staged": 1}

    def commit(_state: Mini) -> dict:
        return {"committed": True}

    graph = StateGraph(Mini)
    graph.add_node("stage", stage)
    graph.add_node("hitl_commit", commit)
    graph.add_edge(START, "stage")
    graph.add_edge("stage", "hitl_commit")
    graph.add_edge("hitl_commit", END)
    app = graph.compile(checkpointer=MemorySaver(), interrupt_before=["hitl_commit"])
    cfg = {"configurable": {"thread_id": "pr-hitl-demo"}}

    first = app.invoke({}, cfg)
    snap = app.get_state(cfg)
    assert snap.next == ("hitl_commit",)
    assert first.get("committed") is None
    assert first.get("staged") == 1

    second = app.invoke(None, cfg)
    assert second["committed"] is True
    assert app.get_state(cfg).next == ()


def test_short_term_cung_thread_id_nho_history():
    """Reducer + thread_id: lượt 2 thấy history lượt 1 (mini-graph, không cần Postgres)."""

    class Mini(TypedDict, total=False):
        history: Annotated[list, _append_trim]

    def add_turn(_state: Mini) -> dict:
        return {"history": [{"role": "user", "content": "hi"}]}

    graph = StateGraph(Mini)
    graph.add_node("add_turn", add_turn)
    graph.add_edge(START, "add_turn")
    graph.add_edge("add_turn", END)
    app = graph.compile(checkpointer=MemorySaver())
    cfg = {"configurable": {"thread_id": "pr-stm-demo"}}

    first = app.invoke({}, cfg)
    second = app.invoke({}, cfg)
    other = app.invoke({}, {"configurable": {"thread_id": "pr-stm-other"}})

    assert len(first["history"]) == 1
    assert len(second["history"]) == 2
    assert len(other["history"]) == 1
