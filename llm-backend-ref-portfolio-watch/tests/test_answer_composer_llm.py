"""LLM AnswerComposer — mock chat + Prompt Registry."""

from __future__ import annotations

from src.portfolio_watch.domain.agents.answer_composer import (
    HeuristicAnswerDraftBrain,
    LlmAnswerDraftBrain,
    run_answer_composer,
)
from src.portfolio_watch.domain.agents.news_agent import NewsAgentResult
from src.portfolio_watch.domain.agents.price_agent import PriceAgentResult
from src.portfolio_watch.domain.ports import NewsItem
from src.portfolio_watch.domain.guardrails.output_checks import check_output


def test_llm_answer_uses_registry_and_plain_text():
    seen: list[str] = []

    def fake_chat(messages, params=None):
        seen.append(messages[0]["content"])
        return (
            "FPT giá đóng cửa 100.0, thay đổi -2.00%. "
            "Tin: FPT giảm nhẹ. Thông tin tham khảo, không phải lời khuyên đầu tư."
        )

    price = PriceAgentResult("FPT", 100.0, 102.0, -2.0)
    news = NewsAgentResult(
        symbol="FPT",
        items=[NewsItem(title="FPT giảm nhẹ", snippet="FPT")],
        tool_calls=1,
    )
    result = run_answer_composer(
        question="FPT dạo này sao?",
        symbol="FPT",
        price=price,
        news=news,
        eval_result=None,
        brain=LlmAnswerDraftBrain(chat_fn=fake_chat),
    )
    assert result.hitl_used is False
    assert result.draft_attempts == 1
    assert "100.0" in result.answer or "100" in result.answer
    assert "nên mua" not in result.answer.lower()
    assert "FPT" in seen[0]
    assert "change_pct=-2.00%" in seen[0] or "-2.00" in seen[0]
    assert "$question" not in seen[0]
    assert check_output("", result.answer, result.evidence).ok


def test_llm_answer_rewrite_on_buy_advice():
    responses = iter(
        [
            "Bạn nên mua FPT ngay. change_pct=-2.00%.",
            "FPT change_pct=-2.00%. Thông tin tham khảo, không phải lời khuyên đầu tư.",
        ]
    )
    prompts: list[str] = []

    def fake_chat(messages, params=None):
        prompts.append(messages[0]["content"])
        return next(responses)

    price = PriceAgentResult("FPT", 98.0, 100.0, -2.0)
    result = run_answer_composer(
        question="FPT sao?",
        symbol="FPT",
        price=price,
        news=None,
        eval_result=None,
        brain=LlmAnswerDraftBrain(chat_fn=fake_chat),
    )
    assert result.draft_attempts > 1
    assert "nên mua" not in result.answer.lower()
    assert result.hitl_used is False
    assert len(prompts) >= 2
    assert "nên mua" in prompts[1].lower() or "vi phạm" in prompts[1].lower()


def test_llm_answer_empty_raises_then_fallback_clean():
    def empty_chat(messages, params=None):
        return "   "

    price = PriceAgentResult("FPT", 100.0, 100.0, 0.0)
    result = run_answer_composer(
        question="FPT?",
        symbol="FPT",
        price=price,
        news=None,
        eval_result=None,
        brain=LlmAnswerDraftBrain(chat_fn=empty_chat),
        max_attempts=2,
    )
    assert "nên mua" not in result.answer.lower()
    assert result.hitl_used is False
    assert check_output("", result.answer, result.evidence).ok


def test_llm_answer_respects_production_prompt_version(tmp_path, monkeypatch):
    import yaml
    from src.portfolio_watch.infra.llm import prompt_registry as pr

    name = "answer_compose"
    d = tmp_path / name
    d.mkdir()
    (d / "production.txt").write_text("1\n", encoding="utf-8")
    for ver, marker in ((1, "ANS_V1"), (2, "ANS_V2")):
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
                        f"{marker} q=$question sym=$symbol price=$price_summary "
                        f"news=$news_summary eval=$eval_summary "
                        f"evid=$evidence viol=$violations"
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
        return "FPT change_pct=0.00%. Thông tin tham khảo, không phải lời khuyên đầu tư."

    price = PriceAgentResult("FPT", 100.0, 100.0, 0.0)
    run_answer_composer(
        question="Giá FPT?",
        symbol="FPT",
        price=price,
        news=None,
        eval_result=None,
        brain=LlmAnswerDraftBrain(chat_fn=fake_chat, prompt_version="production"),
    )
    assert "ANS_V1" in seen[-1]

    (d / "production.txt").write_text("2\n", encoding="utf-8")
    run_answer_composer(
        question="Giá FPT?",
        symbol="FPT",
        price=price,
        news=None,
        eval_result=None,
        brain=LlmAnswerDraftBrain(chat_fn=fake_chat, prompt_version="production"),
    )
    assert "ANS_V2" in seen[-1]
    pr.registry.cache_clear()


def test_heuristic_answer_still_injectable():
    price = PriceAgentResult("FPT", 100.0, 100.0, 0.0)
    result = run_answer_composer(
        question="FPT?",
        symbol="FPT",
        price=price,
        news=None,
        eval_result=None,
        brain=HeuristicAnswerDraftBrain(),
    )
    assert result.draft_attempts == 1
    assert "100" in result.answer
    assert result.hitl_used is False
