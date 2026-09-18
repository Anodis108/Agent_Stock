"""Multi-symbol rewrite — Phase 3a comparison slice."""

from __future__ import annotations

from src.portfolio_watch.domain.agents.supervisor import (
    HeuristicRewriteBrain,
    _extract_symbols,
    rewrite_question,
)


def test_extract_symbols_ignores_tin_from_news_phrase():
    assert _extract_symbols(
        "Giải thích biến động giá HPG gần đây dựa trên tin tức"
    ) == ["HPG"]


def test_heuristic_rewrite_volatility_question_is_explain():
    rw = HeuristicRewriteBrain().rewrite(
        "FPT và HPG mã nào biến động mạnh hơn gần đây?", []
    )
    assert rw.symbols == ["FPT", "HPG"]
    assert rw.intent == "explain"


def test_heuristic_rewrite_multi_symbol_comparison():
    rw = HeuristicRewriteBrain().rewrite(
        "So sánh giá FPT và VNM hôm nay", []
    )
    assert rw.symbols == ["FPT", "VNM"]
    assert rw.symbol == "FPT"
    assert rw.intent == "explain"


def test_llm_rewrite_merges_symbols_from_question_when_llm_returns_one():
    def fake_chat(messages, params):
        return (
            '{"rewritten":"So sánh giá FPT và VNM",'
            '"symbol":"FPT","intent":"explain"}'
        )

    rw = rewrite_question(
        "So sánh giá FPT và VNM hôm nay",
        [],
        brain=__import__(
            "src.portfolio_watch.domain.agents.supervisor", fromlist=["LlmRewriteBrain"]
        ).LlmRewriteBrain(chat_fn=fake_chat),
    )
    assert rw.symbol == "FPT"
    assert rw.symbols == ["FPT", "VNM"]
