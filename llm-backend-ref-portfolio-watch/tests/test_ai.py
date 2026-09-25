"""AI service + LangGraph — dependency thật (vnstock, Cafef, SQLite)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.ai_main import app
from backend.graph.chat import compile_chat_graph, run_chat_graph
from backend.graph.scan import compile_scan_graph


@pytest.fixture
def ai_client(real_deps):
    return TestClient(app)


def test_ai_v1_chat_and_scan(ai_client):
    chat = ai_client.post("/v1/chat", json={"question": "Giá FPT hiện tại?"})
    assert chat.status_code == 200
    data = chat.json()
    assert data["answer"]
    names = [s["name"] for s in data["steps"]]
    assert "rewrite_question" in names and "answer_composer" in names

    scan = ai_client.post("/v1/scan", json={"symbol": "FPT"})
    assert scan.status_code == 200
    snames = [s["name"] for s in scan.json()["steps"]]
    assert "price_agent" in snames and "news_agent" in snames


def test_chat_graph_compile_and_invoke(real_deps):
    g = compile_chat_graph()
    nodes = set(g.get_graph(xray=True).nodes.keys())
    assert {"rewrite_question", "supervisor", "workers", "answer_composer"} <= nodes

    result = run_chat_graph(
        "Giá FPT hôm nay?",
        price_source=real_deps.price_source,
        news_source=real_deps.news_source,
        history_store=real_deps.history_store,
        memory_store=real_deps.memory_store,
        turn="t1",
    )
    assert result.answer and any(s["name"] == "rewrite_question" for s in result.steps)


def test_scan_graph_compiles():
    g = compile_scan_graph()
    nodes = set(g.get_graph(xray=True).nodes.keys())
    assert "fetch" in nodes and "event_classifier" in nodes
