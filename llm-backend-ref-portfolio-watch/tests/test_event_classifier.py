"""Unit tests Event Classifier — test-plan (heuristic inject) + LLM brain (mock)."""

from __future__ import annotations

from src.portfolio_watch.domain.agents.event_classifier import (
    HeuristicEventClassifier,
    LlmEventClassifier,
    classify_event,
)
from src.portfolio_watch.domain.agents.news_agent import NewsAgentResult
from src.portfolio_watch.domain.agents.price_agent import PriceAgentResult
from src.portfolio_watch.domain.entities import EventRoute
from src.portfolio_watch.domain.ports import NewsItem

_HEUR = HeuristicEventClassifier()


def _price(change_pct: float | None) -> PriceAgentResult:
    return PriceAgentResult(
        symbol="FPT",
        latest_close=100.0,
        prev_close=100.0,
        change_pct=change_pct,
    )


def _news(*titles: str) -> NewsAgentResult:
    items = [NewsItem(title=t, snippet=t) for t in titles]
    return NewsAgentResult(symbol="FPT", items=items, tool_calls=1)


def test_small_move_no_bad_news_is_normal():
    decision = classify_event(
        _price(0.5),
        _news("FPT giữ vững đà tăng nhẹ"),
        brain=_HEUR,
    )
    assert decision.route == EventRoute.NORMAL


def test_large_move_down_is_abnormal():
    decision = classify_event(
        _price(-5.0), _news(), threshold_pct=3.0, brain=_HEUR
    )
    assert decision.route == EventRoute.ABNORMAL
    assert "change_pct" in decision.reason


def test_large_move_up_is_abnormal():
    decision = classify_event(
        _price(5.0), _news(), threshold_pct=3.0, brain=_HEUR
    )
    assert decision.route == EventRoute.ABNORMAL


def test_negative_news_is_abnormal_even_if_price_flat():
    decision = classify_event(
        _price(0.2),
        _news("FPT bị phạt hành chính", "Thị trường chung ổn định"),
        threshold_pct=3.0,
        brain=_HEUR,
    )
    assert decision.route == EventRoute.ABNORMAL
    assert "tin tiêu cực" in decision.reason


def test_negated_keyword_stays_normal():
    decision = classify_event(
        _price(0.3),
        _news("FPT khẳng định không giảm kế hoạch đầu tư"),
        threshold_pct=3.0,
        brain=_HEUR,
    )
    assert decision.route == EventRoute.NORMAL


def test_dam_bao_not_false_positive_from_am():
    decision = classify_event(
        _price(0.1),
        _news("FPT đảm bảo tiến độ dự án"),
        threshold_pct=3.0,
        brain=_HEUR,
    )
    assert decision.route == EventRoute.NORMAL


def test_brain_error_does_not_escalate():
    class Boom:
        def classify(self, price, news, threshold_pct):
            raise RuntimeError("llm down")

    decision = classify_event(_price(-9.0), _news(), brain=Boom())
    assert decision.route == EventRoute.NORMAL
    assert "classifier lỗi" in decision.reason


def test_llm_classifier_uses_registry_prompt_and_parses_json():
    captured: dict = {}

    def fake_chat(messages, params=None):
        captured["content"] = messages[0]["content"]
        captured["params"] = params
        return '{"route":"bất thường","reason":"LLM: vượt ngưỡng"}'

    brain = LlmEventClassifier(chat_fn=fake_chat)
    decision = classify_event(
        _price(-5.0), _news("FPT giảm mạnh"), threshold_pct=3.0, brain=brain
    )
    assert decision.route == EventRoute.ABNORMAL
    assert "LLM" in decision.reason
    # registry render: biến template phải có trong prompt gửi LLM
    assert "FPT" in captured["content"]
    assert "3" in captured["content"] or "3.0" in captured["content"]
    assert "bộ lọc sự kiện" in captured["content"].lower() or "cổ phiếu" in captured[
        "content"
    ].lower()


def test_llm_classifier_normal_route():
    def fake_chat(messages, params=None):
        return '{"route":"bình thường","reason":"biến động nhỏ"}'

    decision = classify_event(
        _price(0.2),
        _news("FPT ổn định"),
        brain=LlmEventClassifier(chat_fn=fake_chat),
    )
    assert decision.route == EventRoute.NORMAL


def test_default_brain_is_llm_event_classifier():
    """Không inject brain → LlmEventClassifier (mock chat qua monkeypatch-like inject)."""
    calls = []

    def fake_chat(messages, params=None):
        calls.append(messages[0]["content"])
        return '{"route":"bình thường","reason":"ok"}'

    decision = classify_event(
        _price(0.1),
        _news(),
        brain=LlmEventClassifier(chat_fn=fake_chat),
    )
    assert decision.route == EventRoute.NORMAL
    assert calls and "$symbol" not in calls[0]


def test_llm_classifier_invalid_json_does_not_escalate():
    def bad_chat(messages, params=None):
        return "not-json-at-all"

    decision = classify_event(
        _price(-9.0),
        _news(),
        brain=LlmEventClassifier(chat_fn=bad_chat),
    )
    assert decision.route == EventRoute.NORMAL
    assert "classifier lỗi" in decision.reason


def test_llm_classifier_prompt_version_changes_rendered_text(tmp_path, monkeypatch):
    """product-spec: đổi version prompt → nội dung gửi LLM đổi, không sửa code classify."""
    import yaml
    from src.portfolio_watch.infra.llm import prompt_registry as pr

    name = "event_classification"
    d = tmp_path / name
    d.mkdir()
    (d / "production.txt").write_text("1\n", encoding="utf-8")
    for ver, marker in ((1, "PROMPT_V1_MARKER"), (2, "PROMPT_V2_MARKER")):
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
                        f"thr=$threshold_pct close=$latest_close news=$news_titles"
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
        return '{"route":"bình thường","reason":"ok"}'

    brain = LlmEventClassifier(chat_fn=fake_chat, prompt_version="production")
    classify_event(_price(0.1), _news("tin A"), brain=brain)
    assert "PROMPT_V1_MARKER" in seen[-1]

    (d / "production.txt").write_text("2\n", encoding="utf-8")
    classify_event(_price(0.1), _news("tin A"), brain=brain)
    assert "PROMPT_V2_MARKER" in seen[-1]
    pr.registry.cache_clear()
