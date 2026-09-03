"""Live supervisor: LLM chọn worker mỗi vòng (routing động, không lập plan 1 lần).

    python -m pytest tests/test_supervisor_agent.py -s -q
"""

from __future__ import annotations

import sys

from app.agent_pr.supervisor_agent import Agent_Input, run_supervisor
from app.agent_pr.supervisor_agent.nodes import route_supervisor

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def test_route_supervisor_worker_domain():
    assert route_supervisor({"next_agent": "price_agent"}) == "price_agent"
    assert route_supervisor({"next_agent": "db_write"}) == "db_write"


def test_route_supervisor_done_di_final_answer():
    assert route_supervisor({"next_agent": "done"}) == "final_answer"
    assert route_supervisor({}) == "final_answer"


def test_route_supervisor_gia_tri_la_di_final_answer():
    """next_agent LLM trả không nằm trong danh sách worker → coi như done, không crash."""
    assert route_supervisor({"next_agent": "khong_ton_tai"}) == "final_answer"


def test_hpg_online():
    out = run_supervisor(
        Agent_Input(symbol="HPG", thread_id="test-hpg-online", skip_hitl=True)
    )
    print()
    print("answer:", out.answer)
    for step in out.trace:
        print("trace :", step)
    if out.price:
        print("pct   :", out.price.pct_change, "| tin:", len(out.news.articles) if out.news else 0)

    assert out.symbol == "HPG"
    assert "HPG" in out.answer
    assert out.price is not None and out.price.last > 0
    assert out.news is not None and out.news.articles
    assert out.eval is not None
    # Dữ liệu vnstock thật — pct_change có thể = 0 (giá đi ngang), không phải
    # lúc nào cũng tăng/giảm. Chấp nhận cả 3 khả năng, chỉ chặn im lặng bỏ qua.
    assert any(kw in out.answer for kw in ("giảm", "tăng", "không thay đổi", "0.0%", "0%"))


def test_multi_symbol_hpg_fpt_online():
    """2 mã cùng lúc — routing gọi từng worker theo từng mã, câu trả lời so sánh cả hai."""
    out = run_supervisor(
        Agent_Input(
            symbols=["HPG", "FPT"],
            question="HPG và FPT mã nào mạnh hơn hôm nay",
            thread_id="test-multi-hpg-fpt",
            skip_hitl=True,
        )
    )
    print()
    print("answer:", out.answer)
    for step in out.trace:
        print("trace :", step)

    assert out.symbols == ["HPG", "FPT"]
    assert "HPG" in out.answer and "FPT" in out.answer
    assert "HPG" in out.price_by_symbol and "FPT" in out.price_by_symbol
    assert "HPG" in out.news_by_symbol and "FPT" in out.news_by_symbol


def test_chi_gia_khong_goi_news(monkeypatch):
    """Routing chỉ chọn price_agent rồi done → graph không chạy news/eval."""

    calls = {"n": 0}

    def fake_supervisor_node(state):
        calls["n"] += 1
        if calls["n"] == 1:
            return {"next_agent": "price_agent", "trace": list(state.get("trace") or []) + ["chỉ hỏi giá"]}
        return {"next_agent": "done", "trace": list(state.get("trace") or []) + ["đã có giá"]}

    monkeypatch.setattr(
        "app.agent_pr.supervisor_agent.graph.supervisor_node", fake_supervisor_node
    )
    from app.agent_pr.supervisor_agent.graph import _build_graph

    _build_graph.cache_clear()
    try:
        out = run_supervisor(
            Agent_Input(
                symbol="HPG",
                question="giá HPG hôm nay bao nhiêu",
                thread_id="test-chi-gia",
                skip_hitl=True,
            )
        )
    finally:
        _build_graph.cache_clear()
    print()
    print("answer:", out.answer)
    for step in out.trace:
        print("trace :", step)

    assert out.price is not None and out.price.last > 0
    assert out.news is None
    assert out.eval is None
    assert "HPG" in out.answer
