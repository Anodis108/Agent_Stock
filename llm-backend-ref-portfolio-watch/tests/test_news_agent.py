"""Unit tests NewsAgent — test-plan (heuristic) + LLM brain (mock)."""

from __future__ import annotations

from src.portfolio_watch.domain.agents.news_agent import (
    HeuristicNewsBrain,
    LlmNewsBrain,
    NewsReactAction,
    run_news_agent,
)
from src.portfolio_watch.domain.ports import NewsItem
from tests.fakes import FakeNewsSource


def test_filters_out_unrelated_news():
    src = FakeNewsSource(
        [
            [
                NewsItem(title="Thị trường chung tăng điểm", snippet="VN-Index"),
                NewsItem(title="Giá vàng thế giới", snippet="USD"),
            ]
        ]
    )
    brain = HeuristicNewsBrain(min_relevant=1, queries=["FPT"])
    result = run_news_agent("FPT", src, brain, max_steps=3)
    assert result.error is None
    assert result.items == []
    assert result.tool_calls == 1


def test_react_loop_calls_tool_twice_then_stops():
    """Lần 1 tin rác → chưa đủ; lần 2 có tin FPT → finish (không lặp vô hạn)."""
    src = FakeNewsSource(
        [
            [NewsItem(title="Tin vĩ mô", snippet="lạm phát")],
            [
                NewsItem(title="FPT công bố kết quả quý", snippet="FPT lãi tăng"),
                NewsItem(title="Unrelated bank news", snippet="VCB"),
            ],
            [NewsItem(title="should not be fetched", snippet="FPT")],
        ]
    )
    brain = HeuristicNewsBrain(min_relevant=1, queries=["macro", "FPT kết quả"])
    result = run_news_agent("FPT", src, brain, max_steps=5)
    assert result.error is None
    assert result.tool_calls == 2
    assert len(src.calls) == 2
    assert len(result.items) == 1
    assert "FPT" in result.items[0].title.upper()


def test_max_steps_caps_infinite_loop():
    class AlwaysSearch:
        def decide(self, symbol, gathered, step):
            return NewsReactAction(kind="search", query=f"q{step}")

        def filter_relevant(self, symbol, items):
            return items

    src = FakeNewsSource([[NewsItem(title="x", snippet="y")] for _ in range(10)])
    result = run_news_agent("FPT", src, AlwaysSearch(), max_steps=3)
    assert result.tool_calls == 3
    assert len(src.calls) == 3


def test_fetch_error_keeps_prior_relevant_items():
    class BoomAfterFirst(FakeNewsSource):
        def fetch_news(self, symbol, query=None, *, days=None):
            self.calls.append((symbol, query, days))
            if len(self.calls) == 1:
                return [NewsItem(title="FPT tin 1", snippet="FPT")]
            raise RuntimeError("cafef down")

    src = BoomAfterFirst([])
    brain = HeuristicNewsBrain(min_relevant=99, queries=["a", "b"])
    result = run_news_agent("FPT", src, brain, max_steps=5)
    assert result.tool_calls == 2
    assert len(result.items) == 1
    assert result.error is not None
    assert "không lấy được tin" in result.error


def test_llm_news_brain_uses_registry_and_parses_search_then_finish():
    """LLM decide: search → fetch → finish; filter heuristic bỏ tin không liên quan."""
    calls: list[str] = []
    responses = iter(
        [
            '{"kind":"search","query":"FPT kết quả"}',
            '{"kind":"finish","query":null}',
        ]
    )

    def fake_chat(messages, params=None):
        calls.append(messages[0]["content"])
        return next(responses)

    src = FakeNewsSource(
        [
            [
                NewsItem(title="Tin vĩ mô", snippet="lạm phát"),
                NewsItem(title="FPT lãi quý tăng", snippet="FPT"),
            ]
        ]
    )
    brain = LlmNewsBrain(chat_fn=fake_chat, days=7)
    result = run_news_agent("FPT", src, brain, days=7, max_steps=5)
    assert result.error is None
    assert result.tool_calls == 1
    assert len(result.items) == 1
    assert "FPT" in result.items[0].title.upper()
    assert len(calls) == 2
    assert "FPT" in calls[0]
    assert "newsagent" in calls[0].lower().replace(" ", "") or "cafef" in calls[0].lower()
    assert "$symbol" not in calls[0]


def test_llm_news_brain_invalid_json_surfaces_error():
    def bad_chat(messages, params=None):
        return "not-json"

    result = run_news_agent(
        "FPT",
        FakeNewsSource([[]]),
        LlmNewsBrain(chat_fn=bad_chat),
        max_steps=2,
    )
    assert result.items == []
    assert result.error is not None
    assert "không lấy được tin" in result.error


def test_llm_news_brain_respects_production_prompt_version(tmp_path, monkeypatch):
    """product-spec: đổi production.txt → prompt gửi LLM đổi."""
    import yaml
    from src.portfolio_watch.infra.llm import prompt_registry as pr

    name = "news_agent_react"
    d = tmp_path / name
    d.mkdir()
    (d / "production.txt").write_text("1\n", encoding="utf-8")
    for ver, marker in ((1, "NEWS_V1"), (2, "NEWS_V2")):
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
                        f"{marker} symbol=$symbol days=$days step=$step "
                        f"gathered=$gathered_summary"
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
        return '{"kind":"finish","query":null}'

    brain = LlmNewsBrain(chat_fn=fake_chat, prompt_version="production")
    run_news_agent("FPT", FakeNewsSource([[]]), brain, max_steps=1)
    assert "NEWS_V1" in seen[-1]

    (d / "production.txt").write_text("2\n", encoding="utf-8")
    run_news_agent("FPT", FakeNewsSource([[]]), brain, max_steps=1)
    assert "NEWS_V2" in seen[-1]
    pr.registry.cache_clear()
