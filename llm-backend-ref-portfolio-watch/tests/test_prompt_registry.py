"""Unit tests PromptRegistry — khớp test-plan.md (Phase 8 Prompt Registry)."""

from __future__ import annotations

from pathlib import Path
from string import Template

import pytest
import yaml

from src.portfolio_watch.infra.llm.prompt_registry import (
    PromptRegistry,
    _required_vars,
    registry,
    resolve_prompts_dir,
)

ROOT = Path(__file__).resolve().parents[1]
PROMPTS = ROOT / "prompts"


def _all_vars_for(name: str, reg: PromptRegistry | None = None) -> dict[str, str]:
    reg = reg or PromptRegistry(root=PROMPTS)
    tpl = reg.get(name, "production").template
    return {n: f"<{n}>" for n in _required_vars(tpl)}


def test_resolve_prompts_dir_finds_project_prompts():
    found = resolve_prompts_dir()
    assert found.is_dir()
    assert (found / "event_classification" / "v1.yaml").is_file()


def test_registry_get_production_follows_production_txt():
    """test-plan: registry().get(name, version='production') theo production.txt."""
    prompt = registry().get("event_classification", version="production")
    prod = int(
        (PROMPTS / "event_classification" / "production.txt")
        .read_text(encoding="utf-8")
        .strip()
    )
    assert prompt.version == prod
    assert prompt.name == "event_classification"
    assert prompt.template.strip()
    assert "$symbol" in prompt.template


def test_registry_render_missing_required_var_raises_clear_error():
    """test-plan: thiếu biến bắt buộc → raise rõ, không render thiếu biến."""
    with pytest.raises(ValueError, match="Thiếu biến") as ei:
        registry().render(
            "rewrite_question", version="production", question="Giá FPT?"
        )
    assert "conversation" in str(ei.value)


def test_render_does_not_silently_leave_placeholders():
    """Không dùng safe_substitute — thiếu var phải raise."""
    reg = PromptRegistry(root=PROMPTS)
    with pytest.raises(ValueError, match="Thiếu biến"):
        reg.render("supervisor_routing", version=1, rewritten_question="x")


def test_render_specific_version_not_only_production(tmp_path: Path):
    """test-plan: render(version=<số>) đúng version đó kể cả khi không phải production."""
    name = "demo_prompt"
    d = tmp_path / name
    d.mkdir()
    (d / "production.txt").write_text("1\n", encoding="utf-8")
    for ver, body in ((1, "HELLO_V1"), (2, "HELLO_V2")):
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
                    "template": f"{body} symbol=$symbol",
                },
                allow_unicode=True,
            ),
            encoding="utf-8",
        )
    reg = PromptRegistry(root=tmp_path)
    assert "HELLO_V1" in reg.render(name, version="production", symbol="FPT")
    assert "HELLO_V2" in reg.render(name, version=2, symbol="FPT")
    assert "HELLO_V1" not in reg.render(name, version=2, symbol="FPT")


def test_change_production_txt_switches_render_without_code_change(tmp_path: Path):
    """test-plan: đổi production.txt → render mới, không sửa code gọi."""
    name = "switch_prompt"
    d = tmp_path / name
    d.mkdir()
    for ver, body in ((1, "BODY_A"), (2, "BODY_B")):
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
                    "template": f"{body} $x",
                },
                allow_unicode=True,
            ),
            encoding="utf-8",
        )
    (d / "production.txt").write_text("1\n", encoding="utf-8")
    reg = PromptRegistry(root=tmp_path)

    out1 = reg.render(name, version="production", x="ok")
    assert "BODY_A" in out1

    (d / "production.txt").write_text("2\n", encoding="utf-8")
    out2 = reg.render(name, version="production", x="ok")
    assert "BODY_B" in out2
    assert out1 != out2


def test_render_real_prompt_with_all_vars():
    reg = PromptRegistry(root=PROMPTS)
    vars_ = _all_vars_for("event_classification", reg)
    text = reg.render("event_classification", version=1, **vars_)
    assert "<symbol>" in text
    assert "$symbol" not in text
    leftover = {
        m.group("named") or m.group("braced")
        for m in Template(text).pattern.finditer(text)
        if m.group("named") or m.group("braced")
    }
    assert leftover == set()


def test_change_production_txt_agent_uses_new_version_without_code_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Checklist Phase 8: đổi production.txt → agent dùng version mới,
    không sửa code gọi (cùng brain instance, prompt_version='production').
    """
    from src.portfolio_watch.domain.agents.event_classifier import (
        LlmEventClassifier,
        classify_event,
    )
    from src.portfolio_watch.domain.agents.news_agent import NewsAgentResult
    from src.portfolio_watch.domain.agents.price_agent import PriceAgentResult
    from src.portfolio_watch.infra.llm import prompt_registry as pr

    name = "event_classification"
    d = tmp_path / name
    d.mkdir()
    (d / "production.txt").write_text("1\n", encoding="utf-8")
    for ver, marker in ((1, "AGENT_REG_V1"), (2, "AGENT_REG_V2")):
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

    # Cùng instance + cùng prompt_version="production" — không đổi code agent
    brain = LlmEventClassifier(chat_fn=fake_chat, prompt_version="production")
    price = PriceAgentResult("FPT", 100.0, 100.0, 0.5)
    news = NewsAgentResult(symbol="FPT", items=[], tool_calls=0)

    classify_event(price, news, brain=brain)
    assert "AGENT_REG_V1" in seen[-1]

    (d / "production.txt").write_text("2\n", encoding="utf-8")
    classify_event(price, news, brain=brain)
    assert "AGENT_REG_V2" in seen[-1]
    assert seen[-2] != seen[-1]

    # version cụ thể vẫn lấy v1 dù production đã = 2
    assert "AGENT_REG_V1" in PromptRegistry(root=tmp_path).render(
        name,
        version=1,
        symbol="FPT",
        change_pct="0.5",
        threshold_pct="3",
        latest_close="100",
        news_titles="(không có)",
    )
    pr.registry.cache_clear()


def test_checklist_covers_all_four_test_plan_prompt_registry_cases():
    """Ánh xạ 4 bullet test-plan Prompt Registry → test functions trong file này."""
    import tests.test_prompt_registry as mod

    required = {
        "test_registry_get_production_follows_production_txt",
        "test_registry_render_missing_required_var_raises_clear_error",
        "test_change_production_txt_switches_render_without_code_change",
        "test_render_specific_version_not_only_production",
        "test_change_production_txt_agent_uses_new_version_without_code_change",
    }
    for name in required:
        assert callable(getattr(mod, name)), f"missing {name}"
