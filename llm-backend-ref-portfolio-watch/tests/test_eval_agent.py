"""Unit tests EvalAgent — test-plan (heuristic via conftest) + LLM brain (mock)."""

from __future__ import annotations

from src.portfolio_watch.domain.agents.eval_agent import (
    HeuristicEvalBrain,
    LlmEvalBrain,
    run_eval_agent,
)
from src.portfolio_watch.domain.agents.news_agent import NewsAgentResult
from src.portfolio_watch.domain.agents.price_agent import PriceAgentResult
from src.portfolio_watch.domain.entities import SeverityLevel
from src.portfolio_watch.domain.ports import NewsItem, PriceBar
from tests.fakes import FakePriceHistoryStore


def test_clear_data_skips_price_history():
    price = PriceAgentResult(
        symbol="FPT",
        latest_close=90.0,
        prev_close=100.0,
        change_pct=-10.0,
    )
    news = NewsAgentResult(
        symbol="FPT",
        items=[NewsItem(title="FPT giảm mạnh sau tin xấu", snippet="FPT")],
        tool_calls=1,
    )
    store = FakePriceHistoryStore(
        [PriceBar(date="2026-01-01", close=100.0), PriceBar(date="2026-01-10", close=90.0)]
    )
    result = run_eval_agent(price, news, store)
    assert result.history_calls == 0
    assert store.calls == []
    assert result.severity.confidence >= 0.8
    assert result.severity.evidence


def test_ambiguous_calls_history_and_lowers_confidence_when_unsupported():
    """|%| nhỏ + không tin → gọi history; lịch sử ngược chiều → confidence thấp hơn."""
    price = PriceAgentResult(
        symbol="FPT",
        latest_close=98.0,
        prev_close=100.0,
        change_pct=-2.0,
    )
    news = NewsAgentResult(symbol="FPT", items=[], tool_calls=0)
    store_oppose = FakePriceHistoryStore(
        [
            PriceBar(date="2026-01-01", close=80.0),
            PriceBar(date="2026-01-15", close=100.0),
        ]
    )
    store_support = FakePriceHistoryStore(
        [
            PriceBar(date="2026-01-01", close=110.0),
            PriceBar(date="2026-01-15", close=98.0),
        ]
    )
    opposed = run_eval_agent(price, news, store_oppose)
    supported = run_eval_agent(price, news, store_support)
    assert opposed.history_calls == 1
    assert supported.history_calls == 1
    assert opposed.severity.confidence < supported.severity.confidence
    assert opposed.severity.confidence <= 0.45
    assert "không ủng hộ" in opposed.severity.reasoning


def test_history_store_error_still_returns_severity():
    class BoomStore:
        def read_history(self, symbol: str, days: int = 30):
            raise RuntimeError("db down")

    price = PriceAgentResult(
        symbol="FPT", latest_close=98.0, prev_close=100.0, change_pct=-1.0
    )
    news = NewsAgentResult(symbol="FPT", items=[], tool_calls=0)
    result = run_eval_agent(price, news, BoomStore())
    assert result.history_calls == 1
    assert result.severity.confidence <= 0.35
    assert "Lỗi đọc lịch sử" in result.severity.reasoning


def test_llm_eval_skips_history_when_needs_history_false():
    calls: list[str] = []

    def fake_chat(messages, params=None):
        calls.append(messages[0]["content"])
        return (
            '{"needs_history":false,"level":"high","confidence":0.9,'
            '"reasoning":"LLM: giảm mạnh + tin xấu","evidence":["change_pct=-10"],'
            '"proposed_threshold_pct":5.0,"proposed_related_symbols":null}'
        )

    price = PriceAgentResult(
        symbol="FPT", latest_close=90.0, prev_close=100.0, change_pct=-10.0
    )
    news = NewsAgentResult(
        symbol="FPT",
        items=[NewsItem(title="FPT giảm mạnh", snippet="FPT")],
        tool_calls=1,
    )
    store = FakePriceHistoryStore(
        [PriceBar(date="2026-01-01", close=100.0), PriceBar(date="2026-01-10", close=90.0)]
    )
    result = run_eval_agent(
        price, news, store, brain=LlmEvalBrain(chat_fn=fake_chat)
    )
    assert result.history_calls == 0
    assert store.calls == []
    assert result.severity.level == SeverityLevel.HIGH
    assert result.severity.confidence == 0.9
    assert "LLM" in result.severity.reasoning
    assert result.severity.proposed_threshold_pct == 5.0
    assert len(calls) == 1  # cache reuse trên build_severity
    assert "FPT" in calls[0]
    assert "$symbol" not in calls[0]


def test_llm_eval_requests_history_then_scores():
    responses = iter(
        [
            '{"needs_history":true,"level":"low","confidence":0.4,'
            '"reasoning":"mập mờ","evidence":[],'
            '"proposed_threshold_pct":null,"proposed_related_symbols":null}',
            '{"needs_history":false,"level":"medium","confidence":0.7,'
            '"reasoning":"sau khi có lịch sử","evidence":["history_bars=2"],'
            '"proposed_threshold_pct":null,"proposed_related_symbols":null}',
        ]
    )
    prompts: list[str] = []

    def fake_chat(messages, params=None):
        prompts.append(messages[0]["content"])
        return next(responses)

    price = PriceAgentResult(
        symbol="FPT", latest_close=98.0, prev_close=100.0, change_pct=-2.0
    )
    news = NewsAgentResult(symbol="FPT", items=[], tool_calls=0)
    store = FakePriceHistoryStore(
        [
            PriceBar(date="2026-01-01", close=110.0),
            PriceBar(date="2026-01-15", close=98.0),
        ]
    )
    result = run_eval_agent(
        price, news, store, brain=LlmEvalBrain(chat_fn=fake_chat)
    )
    assert result.history_calls == 1
    assert len(store.calls) == 1
    assert result.severity.level == SeverityLevel.MEDIUM
    assert result.severity.confidence == 0.7
    assert "lịch sử" in result.severity.reasoning
    assert "(chưa có lịch sử)" in prompts[0]
    assert "2026-01-01:110" in prompts[1]


def test_llm_eval_invalid_json_returns_safe_severity():
    def bad_chat(messages, params=None):
        return "not-json"

    price = PriceAgentResult(
        symbol="FPT", latest_close=90.0, prev_close=100.0, change_pct=-10.0
    )
    news = NewsAgentResult(symbol="FPT", items=[], tool_calls=0)
    result = run_eval_agent(
        price, news, FakePriceHistoryStore([]), brain=LlmEvalBrain(chat_fn=bad_chat)
    )
    assert result.severity.level == SeverityLevel.LOW
    assert result.severity.confidence <= 0.2
    assert "eval lỗi" in result.severity.reasoning


def test_llm_eval_respects_production_prompt_version(tmp_path, monkeypatch):
    """product-spec: đổi production.txt → prompt gửi LLM đổi."""
    import yaml
    from src.portfolio_watch.infra.llm import prompt_registry as pr

    name = "eval_severity"
    d = tmp_path / name
    d.mkdir()
    (d / "production.txt").write_text("1\n", encoding="utf-8")
    for ver, marker in ((1, "EVAL_V1"), (2, "EVAL_V2")):
        (d / f"v{ver}.yaml").write_text(
            yaml.dump(
                {
                    "name": name,
                    "version": ver,
                    "model": "gpt-4o-mini",
                    "description": f"v{ver}",
                    "owner": "test",
                    "created": "2026-09-17",
                    "changelog": f"v{ver}",
                    "eval_score": None,
                    "template": (
                        f"{marker} symbol=$symbol change=$change_pct "
                        f"news=$news_summary history=$history_summary"
                    ),
                },
                allow_unicode=True,
            ),
            encoding="utf-8",
        )

    monkeypatch.setattr(pr, "resolve_prompts_dir", lambda: tmp_path)
    pr.registry.cache_clear()
    seen: list[str] = []

    def fake_chat(messages, params=None):
        seen.append(messages[0]["content"])
        return (
            '{"needs_history":false,"level":"low","confidence":0.5,'
            '"reasoning":"ok","evidence":[],'
            '"proposed_threshold_pct":null,"proposed_related_symbols":null}'
        )

    price = PriceAgentResult(
        symbol="FPT", latest_close=100.0, prev_close=100.0, change_pct=0.0
    )
    news = NewsAgentResult(symbol="FPT", items=[], tool_calls=0)
    brain = LlmEvalBrain(chat_fn=fake_chat, prompt_version="production")
    run_eval_agent(price, news, FakePriceHistoryStore([]), brain=brain)
    assert "EVAL_V1" in seen[-1]

    (d / "production.txt").write_text("2\n", encoding="utf-8")
    brain2 = LlmEvalBrain(chat_fn=fake_chat, prompt_version="production")
    run_eval_agent(price, news, FakePriceHistoryStore([]), brain=brain2)
    assert "EVAL_V2" in seen[-1]
    pr.registry.cache_clear()


def test_heuristic_still_injectable():
    price = PriceAgentResult(
        symbol="FPT", latest_close=90.0, prev_close=100.0, change_pct=-10.0
    )
    news = NewsAgentResult(
        symbol="FPT",
        items=[NewsItem(title="FPT giảm", snippet="FPT")],
        tool_calls=1,
    )
    result = run_eval_agent(
        price, news, FakePriceHistoryStore([]), brain=HeuristicEvalBrain()
    )
    assert result.history_calls == 0
    assert result.severity.level == SeverityLevel.HIGH
