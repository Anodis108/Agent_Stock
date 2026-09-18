"""LLM Supervisor / RewriteQuestion — mock chat + Prompt Registry."""

from __future__ import annotations

from src.portfolio_watch.domain.agents.supervisor import (
    LlmRewriteBrain,
    LlmSupervisorBrain,
    RewrittenQuestion,
    rewrite_question,
    route_question,
)


def test_llm_rewrite_parses_json_and_uses_registry():
    seen: list[str] = []

    def fake_chat(messages, params=None):
        seen.append(messages[0]["content"])
        return (
            '{"rewritten":"[FPT] Giá FPT hôm nay thế nào?",'
            '"symbol":"FPT","intent":"price_lookup"}'
        )

    rw = rewrite_question(
        "Giá FPT hôm nay thế nào?",
        [],
        brain=LlmRewriteBrain(chat_fn=fake_chat),
    )
    assert rw.symbol == "FPT"
    assert rw.intent == "price_lookup"
    assert "FPT" in rw.rewritten
    assert "Giá FPT" in seen[0] or "FPT" in seen[0]
    assert "$question" not in seen[0]


def test_llm_rewrite_memory_symbol_from_prompt_conversation():
    def fake_chat(messages, params=None):
        # Model trả symbol từ hội thoại (prompt đã nhúng conversation JSON)
        assert "VNM" in messages[0]["content"]
        return (
            '{"rewritten":"[VNM] Còn mã đó thì sao?",'
            '"symbol":"VNM","intent":"price_lookup"}'
        )

    conversation = [
        {"role": "user", "content": "Cho hỏi về mã VNM"},
        {"role": "assistant", "content": "VNM đang ổn."},
    ]
    rw = rewrite_question(
        "Còn mã đó thì sao?",
        conversation,
        brain=LlmRewriteBrain(chat_fn=fake_chat),
    )
    assert rw.symbol == "VNM"


def test_llm_rewrite_null_symbol_falls_back_to_conversation():
    """LLM quên gắn mã → post-process lấy từ Memory/hội thoại."""

    def fake_chat(messages, params=None):
        return (
            '{"rewritten":"Còn mã đó thì sao?",'
            '"symbol":null,"symbols":[],"intent":"price_lookup"}'
        )

    conversation = [
        {"role": "user", "content": "Cho hỏi về mã VNM"},
        {"role": "assistant", "content": "VNM đang ổn."},
    ]
    rw = rewrite_question(
        "Còn mã đó thì sao?",
        conversation,
        brain=LlmRewriteBrain(chat_fn=fake_chat),
    )
    assert rw.symbol == "VNM"
    assert rw.symbols == ["VNM"]
    assert "VNM" in rw.rewritten.upper()


def test_llm_supervisor_routes_explain_to_eval():
    seen: list[str] = []

    def fake_chat(messages, params=None):
        seen.append(messages[0]["content"])
        return (
            '{"agents_to_call":["price","news","eval"],'
            '"reason":"cần giải thích biến động"}'
        )

    rw = RewrittenQuestion(
        original="Tại sao FPT giảm?",
        rewritten="[FPT] Tại sao FPT giảm?",
        symbol="FPT",
        intent="explain",
    )
    decision = route_question(rw, brain=LlmSupervisorBrain(chat_fn=fake_chat))
    assert decision.agents_to_call == ["price", "news", "eval"]
    assert "eval" in decision.agents_to_call
    assert "FPT" in seen[0]
    assert "explain" in seen[0]
    assert "$rewritten_question" not in seen[0]


def test_llm_supervisor_price_only():
    def fake_chat(messages, params=None):
        return '{"agents_to_call":["price"],"reason":"chỉ hỏi giá"}'

    rw = RewrittenQuestion(
        original="Giá FPT?",
        rewritten="[FPT] Giá FPT?",
        symbol="FPT",
        intent="price_lookup",
    )
    decision = route_question(rw, brain=LlmSupervisorBrain(chat_fn=fake_chat))
    assert decision.agents_to_call == ["price"]
    assert "eval" not in decision.agents_to_call


def test_llm_supervisor_invalid_json_falls_back_price():
    def bad_chat(messages, params=None):
        return "not-json"

    rw = RewrittenQuestion(
        original="Giá FPT?",
        rewritten="Giá FPT?",
        symbol="FPT",
        intent="price_lookup",
    )
    decision = route_question(rw, brain=LlmSupervisorBrain(chat_fn=bad_chat))
    assert decision.agents_to_call == ["price"]
    assert "supervisor lỗi" in decision.reason


def test_llm_rewrite_invalid_json_falls_back():
    def bad_chat(messages, params=None):
        return "not-json"

    rw = rewrite_question(
        "Giá FPT hôm nay?",
        [],
        brain=LlmRewriteBrain(chat_fn=bad_chat),
    )
    assert rw.original == "Giá FPT hôm nay?"
    assert rw.symbol == "FPT"  # heuristic extract trong fallback
    assert rw.intent == "price_lookup"


def test_llm_rewrite_respects_production_prompt_version(tmp_path, monkeypatch):
    import yaml
    from src.portfolio_watch.infra.llm import prompt_registry as pr

    name = "rewrite_question"
    d = tmp_path / name
    d.mkdir()
    (d / "production.txt").write_text("1\n", encoding="utf-8")
    for ver, marker in ((1, "RW_V1"), (2, "RW_V2")):
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
                    "template": f"{marker} q=$question conv=$conversation",
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
        return '{"rewritten":"x","symbol":"FPT","intent":"price_lookup"}'

    rewrite_question(
        "Giá FPT?",
        [],
        brain=LlmRewriteBrain(chat_fn=fake_chat, prompt_version="production"),
    )
    assert "RW_V1" in seen[-1]

    (d / "production.txt").write_text("2\n", encoding="utf-8")
    rewrite_question(
        "Giá FPT?",
        [],
        brain=LlmRewriteBrain(chat_fn=fake_chat, prompt_version="production"),
    )
    assert "RW_V2" in seen[-1]
    pr.registry.cache_clear()


def test_llm_supervisor_respects_production_prompt_version(tmp_path, monkeypatch):
    import yaml
    from src.portfolio_watch.infra.llm import prompt_registry as pr

    name = "supervisor_routing"
    d = tmp_path / name
    d.mkdir()
    (d / "production.txt").write_text("1\n", encoding="utf-8")
    for ver, marker in ((1, "SV_V1"), (2, "SV_V2")):
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
                        f"{marker} q=$rewritten_question "
                        f"sym=$symbol intent=$intent"
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
        return '{"agents_to_call":["price"],"reason":"ok"}'

    rw = RewrittenQuestion("a", "a", "FPT", "price_lookup")
    route_question(
        rw, brain=LlmSupervisorBrain(chat_fn=fake_chat, prompt_version="production")
    )
    assert "SV_V1" in seen[-1]

    (d / "production.txt").write_text("2\n", encoding="utf-8")
    route_question(
        rw, brain=LlmSupervisorBrain(chat_fn=fake_chat, prompt_version="production")
    )
    assert "SV_V2" in seen[-1]
    pr.registry.cache_clear()
