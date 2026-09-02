"""Short-term (thread_id / history) + long-term (user_id / Qdrant) cho agent_pr.

Không gọi OpenAI / vnstock: mock recall/store và mini-graph checkpointer.
"""

from __future__ import annotations

from typing import Annotated, TypedDict

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from pydantic import ValidationError

from app.agent_pr.supervisor_agent.nodes import (
    recall_memory,
    rewrite_question,
    route_supervisor,
    store_memory,
)
from app.agent_pr.supervisor_agent.schemas import Agent_Input
from app.agent_pr.supervisor_agent.state import _append_trim


def test_append_trim_giu_cua_so():
    left = [{"i": i} for i in range(18)]
    right = [{"i": 18}, {"i": 19}, {"i": 20}]
    out = _append_trim(left, right)
    assert len(out) == 20
    assert out[0]["i"] == 1
    assert out[-1]["i"] == 20


def test_route_supervisor_worker_va_done():
    assert route_supervisor({"next_agent": "price_agent"}) == "price_agent"
    assert route_supervisor({"next_agent": "db_agent"}) == "db_agent"
    assert route_supervisor({"next_agent": "db_write"}) == "db_write"
    assert route_supervisor({"next_agent": "eval_agent"}) == "eval_agent"
    assert route_supervisor({"next_agent": "done"}) == "final_answer"
    assert route_supervisor({}) == "final_answer"


def test_recall_khong_user_van_ghi_history():
    out = recall_memory({"question": "giá HPG", "user_id": ""})
    assert out["memories"] == []
    assert out["history"] == [{"role": "user", "content": "giá HPG"}]


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
            "output": type("O", (), {"answer": "HPG giảm 1%."})(),
            "question": "Tôi thích HPG",
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
