"""Scan supervisor agent — chat gather chọn lọc vs scan pipeline tuần tự."""

from __future__ import annotations

from langgraph.graph import END

from ai_backend.domain.agents.scan.scan_supervisor_agent import (
    HeuristicScanSupervisorBrain,
    plan_scan_supervisor,
    scan_supervisor_node,
)


def test_chat_gather_one_worker_at_a_time():
    brain = HeuristicScanSupervisorBrain()
    state = {
        "mode": "chat",
        "gather_request": ["price_agent", "news_agent"],
        "completed": [],
    }
    d = brain.plan(state)
    assert d.next_workers == ["price_agent"]
    assert d.policy == "chat_selective"

    after_price = {
        **state,
        "price": object(),
        "completed": ["price_agent"],
    }
    d2 = brain.plan(after_price)
    assert d2.next_workers == ["news_agent"]

    after_all = {**after_price, "news": object(), "completed": ["price_agent", "news_agent"]}
    d3 = brain.plan(after_all)
    assert d3.next_workers == ["chat_supervisor"]


def test_chat_gather_skips_satisfied_without_completed_flag():
    """Đã có price trong state thì không gọi lại price_agent dù chưa trong completed."""
    state = {
        "mode": "chat",
        "gather_request": ["price_agent", "news_agent"],
        "completed": [],
        "price": object(),
    }
    d = plan_scan_supervisor(state)
    assert d.next_workers == ["news_agent"]


def test_scan_pipeline_sequential_not_parallel_price_news():
    state = {"mode": "scan", "completed": []}
    d = plan_scan_supervisor(state)
    assert d.next_workers == ["price_agent"]
    assert d.policy == "scan_sequential"

    d2 = plan_scan_supervisor({**state, "price": object()})
    assert d2.next_workers == ["news_agent"]


def test_scan_supervisor_node_returns_end():
    out = scan_supervisor_node(
        {
            "mode": "scan",
            "price": object(),
            "news": object(),
            "event_routing": type("R", (), {"route": "normal"})(),
        },
        None,
    )
    assert out["next"] == [END]
