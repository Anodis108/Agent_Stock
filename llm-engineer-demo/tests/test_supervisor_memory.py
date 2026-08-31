"""Short-term (thread_id / history) + long-term (user_id / Qdrant) cho agent_pr.

Không gọi OpenAI / vnstock: mock recall/store và mini-graph checkpointer.
"""

from __future__ import annotations

from typing import Annotated, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.agent_pr.craw_agent.schemas import Agent_Output as PriceOut
from app.agent_pr.news_agent.schemas import Agent_Output as NewsOut
from app.agent_pr.supervisor_agent.nodes import (
    _pending_gather,
    recall_memory,
    store_memory,
)
from app.agent_pr.supervisor_agent.schemas import AgentPlan
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
        "price": PriceOut(symbol="HPG", last=22100),
        "news": NewsOut(symbol="HPG", articles=[]),
    }
    assert _pending_gather(state, plan) == []


def test_pending_gather_gia_rong_thi_fetch_lai():
    plan = AgentPlan(
        symbol="HPG",
        use_price=True,
        use_news=False,
        use_db=False,
        use_eval=False,
        use_synth=True,
        reasoning="giá lỗi",
    )
    state = {"price": PriceOut(symbol="HPG", last=0)}
    assert _pending_gather(state, plan) == ["price_agent"]


def test_recall_khong_user_van_ghi_history():
    out = recall_memory({"question": "giá HPG", "user_id": ""})
    assert out["memories"] == []
    assert out["history"] == [{"role": "user", "content": "giá HPG"}]


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
    from app.llm import completion

    saved: list[tuple[str, str]] = []
    monkeypatch.setattr(completion, "chat", lambda *a, **k: "User theo dõi HPG.")
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


def test_short_term_cung_thread_id_nho_history():
    """MemorySaver + thread_id: lượt 2 thấy history lượt 1 (sliding window)."""

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
