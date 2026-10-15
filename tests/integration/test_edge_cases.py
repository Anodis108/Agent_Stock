"""Tests for Task 5.2: Edge Cases & Fallbacks Handling.

Covers:
1. Unknown / non-existent ticker (e.g. XYZ) -> graceful polite message & suggestions.
2. Empty portfolio state -> clear guidance to add the first stock (both Web UI and Chat).
3. LLM failure -> Provider Cascade (Ollama / vLLM) and Heuristic Fallback engine.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

from backend.agents.answer_composer.nodes import (
    HeuristicAnswerDraftBrain,
    LlmAnswerDraftBrain,
    build_evidence,
    run_answer_composer,
)
from backend.agents.price_agent.nodes import run_price_agent
from backend.domain.ports import PriceQuote
from backend.graph.chat import build_chat_graph
from backend.infra.llm.providers import call_with_backend_fallback, resolve_backend_chain


def test_edge_case_unknown_ticker_xyz_price_and_composer(monkeypatch):
    """Mã không tồn tại (VD: XYZ): Thông báo không tìm thấy mã và gợi ý tra cứu mã VN30."""
    mock_price_source = MagicMock()
    mock_price_source.fetch_latest_close.return_value = PriceQuote(
        symbol="XYZ",
        latest_close=None,
        error="Không tìm thấy dữ liệu giá cho mã 'XYZ' hoặc mã không tồn tại trên thị trường.",
    )

    price_res = run_price_agent("XYZ", mock_price_source)
    assert price_res.symbol == "XYZ"
    assert price_res.latest_close is None
    assert "không tìm thấy dữ liệu giá" in price_res.error.lower()

    # Soạn câu trả lời bằng HeuristicAnswerDraftBrain
    evidence = build_evidence(price_res, None, None)
    brain = HeuristicAnswerDraftBrain()
    ans = brain.compose(
        question="Giá cổ phiếu XYZ hôm nay thế nào?",
        symbol="XYZ",
        price=price_res,
        news=None,
        eval_result=None,
        evidence=evidence,
        model="heuristic",
        attempt=0,
        previous_violations=[],
    )

    assert "XYZ" in ans
    assert ("không tìm thấy" in ans.lower() or "không tồn tại" in ans.lower())
    assert "Gợi ý" in ans or "gợi ý" in ans or "FPT" in ans


def test_edge_case_empty_portfolio_chat_guidance():
    """Danh mục rỗng: Chat bot thông báo danh mục rỗng và hướng dẫn thêm mã đầu tiên."""
    mock_summary = MagicMock()
    mock_summary.items = []
    mock_summary.user_id = "test_user_empty"
    mock_summary.count = 0
    mock_summary.total_nav = 0.0
    mock_summary.total_cost = 0.0
    mock_summary.total_unrealized_pnl = 0.0
    mock_summary.total_pnl_pct = 0.0

    evidence = build_evidence(None, None, None, portfolio_summary=mock_summary)
    assert "portfolio_status:empty" in evidence
    assert any("portfolio_guide:" in e for e in evidence)

    brain = HeuristicAnswerDraftBrain()
    ans = brain.compose(
        question="Danh mục của tôi hiện tại thế nào?",
        symbol=None,
        price=None,
        news=None,
        eval_result=None,
        evidence=evidence,
        model="heuristic",
        attempt=0,
        previous_violations=[],
    )

    assert "chưa có cổ phiếu nào" in ans.lower() or "danh mục rỗng" in ans.lower()
    assert "Bước 1" in ans
    assert "Bước 2" in ans
    assert "Bước 3" in ans


def test_edge_case_llm_provider_cascade_resolution(monkeypatch):
    """Khi primary backend là openai và không có config tùy biến, tự động cascade sang ollama, vllm."""
    from backend.shared.settings import settings

    monkeypatch.setattr(settings, "llm_backend", "openai")
    monkeypatch.setattr(settings, "llm_fallback_backends", "")

    chain = resolve_backend_chain()
    assert chain[0] == "openai"
    assert "ollama" in chain
    assert "vllm" in chain


def test_edge_case_llm_fallback_cascade_execution():
    """Khi primary provider lỗi, call_with_backend_fallback thử provider tiếp theo."""
    attempts = []

    def mock_backend_fn(backend_name: str | None):
        attempts.append(backend_name)
        if backend_name == "openai" or backend_name is None:
            raise ConnectionError("OpenAI API unreachable")
        if backend_name == "ollama":
            return "SUCCESS_FROM_OLLAMA"
        return "SUCCESS"

    with patch("backend.infra.llm.providers.resolve_backend_chain", return_value=["openai", "ollama", "vllm"]):
        result = call_with_backend_fallback(mock_backend_fn)
        assert result == "SUCCESS_FROM_OLLAMA"
        assert attempts == [None, "ollama"]


def test_edge_case_all_llm_providers_fail_triggers_heuristic_fallback():
    """Khi toàn bộ LLM provider đều lỗi, run_answer_composer tự động fallback sang Heuristic."""
    mock_broken_brain = MagicMock()
    mock_broken_brain.compose.side_effect = RuntimeError("All LLM providers timed out")

    mock_price = MagicMock()
    mock_price.symbol = "FPT"
    mock_price.latest_close = 66.0
    mock_price.prev_close = 65.0
    mock_price.change_pct = 1.54
    mock_price.error = None

    result = run_answer_composer(
        question="Giá FPT bao nhiêu?",
        symbol="FPT",
        price=mock_price,
        news=None,
        eval_result=None,
        brain=mock_broken_brain,
    )

    assert result is not None
    assert result.answer != ""
    assert "FPT" in result.answer
    assert "66" in result.answer
    # Không văng lỗi và đã sinh ra câu trả lời dựa trên Heuristic
    assert result.guardrail_violations == []


def test_edge_case_frontend_empty_state_and_styles():
    """Kiểm tra file frontend app.js và style.css chứa đầy đủ cấu trúc UI empty state danh mục."""
    with open("src/frontend/app.js", encoding="utf-8") as f:
        app_js = f.read()
    assert "portfolio-empty-state" in app_js
    assert "Danh mục đang trống" in app_js
    assert "Bước 1:" in app_js
    assert "Bước 2:" in app_js
    assert "Bước 3:" in app_js

    with open("src/frontend/style.css", encoding="utf-8") as f:
        style_css = f.read()
    assert ".portfolio-empty-state" in style_css
    assert ".portfolio-empty-cell" in style_css
    assert ".empty-state-steps" in style_css


def test_edge_case_chat_endpoint_unknown_ticker(client):
    """Gửi câu hỏi về mã không tồn tại XYZ qua POST /chat: không văng lỗi 500, thông báo lịch sự."""
    res = client.post(
        "/chat",
        json={"question": "Giá cổ phiếu XYZ hôm nay thế nào?", "session_id": "test_edge_xyz"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data.get("answer") is not None
    ans = data["answer"]
    assert "XYZ" in ans
    assert ("không tìm thấy" in ans.lower() or "không tồn tại" in ans.lower())


def test_edge_case_chat_endpoint_empty_portfolio(client):
    """Gửi câu hỏi về danh mục cho user mới qua POST /chat: hướng dẫn thêm mã đầu tiên."""
    res = client.post(
        "/chat",
        json={"question": "Danh mục của tôi hiện có những gì?", "session_id": "test_edge_empty_port"},
        headers={"X-User-ID": "user_empty_tester"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data.get("answer") is not None
    ans = data["answer"]
    assert ("chưa có cổ phiếu nào" in ans.lower() or "danh mục rỗng" in ans.lower() or "danh mục" in ans.lower())

