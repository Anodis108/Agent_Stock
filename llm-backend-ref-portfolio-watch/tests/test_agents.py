"""Kiểm thử Agent Nodes, LangGraph Workflow, Structured Output và Tracing.

Tập trung kiểm tra:
1. Các Agent Nodes: PriceAgent, NewsAgent, EventClassifier, AnswerComposer, Guardrails.
2. Biên dịch và thực thi đồ thị LangGraph (Chat Graph, Scan Graph).
3. Pydantic Schemas và cơ chế Structured Output (Retry, JSON extraction).
4. Hệ thống Tracing (agent_span, runtime telemetry).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from backend.agents import answer_composer, synthesis_agent
from backend.agents.eval_agent.nodes import HeuristicEvalBrain
from backend.agents.eval_agent.schemas import EvalSeverityOutput
from backend.agents.event_classifier import classify_event
from backend.agents.event_classifier.schemas import ClassifierOutput
from backend.agents.news_agent import run_news_agent
from backend.agents.news_agent.schemas import NewsAgentResult, NewsReactOutput
from backend.agents.price_agent import PriceAgentResult, run_price_agent
from backend.agents.supervisor_agent.nodes import (
    HeuristicRewriteBrain,
    HeuristicSupervisorBrain,
    rewrite_question,
    route_question,
)
from backend.agents.supervisor_agent.schemas import RewriteOutput, SupervisorOutput
from backend.agents.synthesis_agent.schemas import SynthesisAlertOutput
from backend.domain.entities import EventRoute, Severity, SeverityLevel
from backend.domain.guardrails.output_checks import check_output
from backend.graph.chat import compile_chat_graph, run_chat_graph
from backend.graph.scan import compile_scan_graph
from backend.infra.llm.structured import (
    call_llm_structured,
    extract_json_str,
    parse_structured,
)
from backend.infra.market_data import CafefNewsSource, VnstockPriceSource
from backend.infra.monitoring.tracing import agent_span, trace_request, reset_client_for_tests


# ==============================================================================
# 1. Agent Execution & Nodes Tests
# ==============================================================================

def test_price_agent_real_vnstock():
    """Kiểm tra PriceAgent truy xuất dữ liệu giá từ Vnstock."""
    r = run_price_agent("FPT", VnstockPriceSource())
    if r.error:
        pytest.skip(f"vnstock không khả dụng: {r.error}")
    assert r.latest_close is not None
    assert r.change_pct is not None


def test_guardrail_blocks_buy_sell_advice():
    """Kiểm tra Guardrail chặn đứng các khuyến nghị mua/bán cổ phiếu."""
    buy = check_output("Alert", "Nhà đầu tư nên mua FPT ngay.", evidence=["change_pct=-4%"])
    sell = check_output("Alert", "Nhà đầu tư nên bán FPT ngay.", evidence=["change_pct=-4%"])
    assert buy.ok is False and sell.ok is False


def test_guardrail_shared_by_synthesis_and_answer():
    """Đảm bảo synthesis_agent và answer_composer dùng chung một hàm kiểm tra guardrail."""
    assert synthesis_agent.nodes.check_output is check_output
    assert answer_composer.nodes.check_output is check_output


def test_event_classifier_with_real_price_and_news():
    """Kiểm tra bộ phân loại sự kiện (EventClassifier) với dữ liệu giá và tin tức."""
    price = run_price_agent("FPT", VnstockPriceSource())
    if price.error:
        pytest.skip(f"vnstock không khả dụng: {price.error}")
    news = run_news_agent("FPT", CafefNewsSource(), days=7)
    routing = classify_event(price, news, threshold_pct=3.0)
    assert routing.route in (EventRoute.NORMAL, EventRoute.ABNORMAL)
    assert routing.reason.strip()


# ==============================================================================
# 2. LangGraph Workflow Tests
# ==============================================================================

def test_chat_graph_compile_and_nodes():
    """Kiểm tra đồ thị Chat Graph biên dịch thành công và chứa đầy đủ các agent node."""
    g = compile_chat_graph()
    nodes = set(g.get_graph(xray=True).nodes.keys())
    expected = {"pre_rewrite_guardrail", "guardrail_refusal", "rewrite_question", "supervisor", "workers", "answer_composer"}
    assert expected <= nodes


def test_chat_graph_execution(real_deps):
    """Kiểm tra luồng thực thi end-to-end của Chat Graph."""
    result = run_chat_graph(
        "Giá FPT hôm nay?",
        price_source=real_deps.price_source,
        news_source=real_deps.news_source,
        history_store=real_deps.history_store,
        memory_store=real_deps.memory_store,
        rewrite_brain=HeuristicRewriteBrain(),
        supervisor_brain=HeuristicSupervisorBrain(),
        turn="t1",
    )
    assert result.answer is not None
    assert len(result.steps) > 0
    step_names = [s["name"] for s in result.steps]
    assert "pre_rewrite_guardrail" in step_names or "rewrite_question" in step_names


def test_scan_graph_compiles():
    """Kiểm tra đồ thị Scan Graph biên dịch thành công."""
    g = compile_scan_graph()
    nodes = set(g.get_graph(xray=True).nodes.keys())
    assert "fetch" in nodes and "event_classifier" in nodes


# ==============================================================================
# 3. Structured Output & Pydantic Schema Validation
# ==============================================================================

def test_rewrite_schema_valid():
    """Kiểm tra schema RewriteOutput chuẩn hóa và deduplicate mã cổ phiếu."""
    out = RewriteOutput(
        rewritten="Giá FPT hôm nay?",
        symbol="fpt",
        symbols=["fpt", "VNM", "none", "FPT"],
        intent="price_lookup",
    )
    assert out.rewritten == "Giá FPT hôm nay?"
    assert out.symbol == "FPT"
    assert out.symbols == ["FPT", "VNM"]
    assert out.intent == "price_lookup"


def test_supervisor_schema_validation():
    """Kiểm tra schema SupervisorOutput chuẩn hóa danh sách sub-agents."""
    out = SupervisorOutput(
        agents_to_call=["PRICE", "NEWS", "price", "UNKNOWN"],  # type: ignore
        reason="Hỏi giá cổ phiếu",
    )
    assert out.agents_to_call == ["price", "news"]
    assert out.reason == "Hỏi giá cổ phiếu"


def test_eval_severity_schema_validation():
    """Kiểm tra schema EvalSeverityOutput với mức độ nghiêm trọng và confidence."""
    out = EvalSeverityOutput(
        level="high",
        confidence=0.85,
        reasoning="Biến động mạnh vượt ngưỡng",
    )
    assert out.level == "high"
    assert out.confidence == 0.85


def test_json_extractor_handles_markdown_codeblocks():
    """Kiểm tra hàm extract_json_str bóc tách JSON chính xác từ phản hồi có chứa ```json."""
    raw = 'Here is the response:\n```json\n{"rewritten": "FPT", "symbol": "FPT", "symbols": ["FPT"], "intent": "price_lookup"}\n```'
    extracted = extract_json_str(raw)
    parsed = parse_structured(extracted, RewriteOutput)
    assert parsed.symbol == "FPT"


def test_call_llm_structured_retry_on_parse_error():
    """Kiểm tra cơ chế retry của call_llm_structured khi LLM trả JSON sai cú pháp ở lần đầu."""
    calls = []

    def fake_chat(messages, params=None):
        calls.append(1)
        if len(calls) == 1:
            return "not a valid json"
        return json.dumps({"agents_to_call": ["price"], "reason": "tra cứu giá"})

    res = call_llm_structured([], SupervisorOutput, chat_fn=fake_chat, max_retries=2)
    assert res.agents_to_call == ["price"]
    assert len(calls) == 2


# ==============================================================================
# 4. Tracing & Agent Span Tests
# ==============================================================================

def test_agent_span_captures_input_and_output(monkeypatch):
    """Kiểm tra context manager agent_span ghi nhận đầy đủ input, output và duration."""
    from backend.shared.settings import settings
    from backend.infra.monitoring import tracing as tracing_mod

    class MockSpan:
        def __init__(self, name, input=None, metadata=None):
            self.name = name
            self.input = input
            self.metadata = metadata or {}
            self.children = []
            self.output = None
            self.ended = False

        def span(self, **kwargs):
            child = MockSpan(name=kwargs.get("name"), input=kwargs.get("input"), metadata=kwargs.get("metadata"))
            self.children.append(child)
            return child

        def start_observation(self, **kwargs):
            return self.span(**kwargs)

        def update(self, **kwargs):
            if "output" in kwargs:
                self.output = kwargs["output"]

        def end(self):
            self.ended = True

    class MockLangfuse:
        def __init__(self):
            self.roots = []

        def trace(self, **kwargs):
            root = MockSpan(name=kwargs.get("name"), input=kwargs.get("input"), metadata=kwargs.get("metadata"))
            self.roots.append(root)
            return root

        def flush(self):
            pass

    monkeypatch.setattr(settings, "monitoring_enabled", True)
    monkeypatch.setattr(settings, "langfuse_public_key", "pk-test")
    monkeypatch.setattr(settings, "langfuse_secret_key", "sk-test")
    monkeypatch.setattr(settings, "langfuse_host", "http://mock-langfuse:3000")

    mock_client = MockLangfuse()
    monkeypatch.setattr(tracing_mod, "_client", mock_client)
    reset_client_for_tests()
    monkeypatch.setattr(tracing_mod, "_client", mock_client)

    monkeypatch.setattr(tracing_mod, "should_sample", lambda **kwargs: True)

    turn = "test_turn_123"
    with trace_request("chat", "FPT", metadata={"turn": turn}):
        with agent_span(turn, "test_node", input={"q": "FPT"}) as box:
            box["output"] = {"status": "ok"}

    assert len(mock_client.roots) == 1
    root = mock_client.roots[0]
    assert root.name == "chat"
    assert len(root.children) == 1
    child = root.children[0]
    assert child.name == "test_node"
    assert child.input == {"q": "FPT"}
    assert child.output == {"status": "ok"}
    assert child.ended is True


# ==============================================================================
# 5. Prompt Registry — Phase 1 (M3-B1)
# ==============================================================================

def test_all_production_llm_prompts_load_from_registry():
    """Mọi prompt LLM production phải có trong resources/prompts/ — không hardcode."""
    from backend.infra.llm.prompt_registry import PRODUCTION_LLM_PROMPT_NAMES, registry

    reg = registry()
    for name in PRODUCTION_LLM_PROMPT_NAMES:
        prompt = reg.get(name, version="production")
        assert prompt.template.strip(), f"Prompt '{name}' có template rỗng"
        assert (reg._root / name / "production.txt").is_file(), (
            f"Prompt '{name}' thiếu production.txt"
        )


def test_eval_system_prompts_use_registry_not_hardcode():
    """Eval judge / task_success / trajectory lấy system prompt từ registry."""
    from backend.eval.run import _get_judge_system_prompt
    from backend.infra.eval.agent_scorers import (
        _get_default_success_criteria,
        _get_task_success_system_prompt,
        _get_trajectory_system_prompt,
    )
    from backend.infra.llm.prompt_registry import get_system_prompt

    assert _get_judge_system_prompt() == get_system_prompt("eval_judge")
    assert _get_task_success_system_prompt() == get_system_prompt("eval_task_success")
    assert _get_trajectory_system_prompt() == get_system_prompt("eval_trajectory")
    assert _get_default_success_criteria()


def test_phase2_prompt_v2_load_metadata_and_render():
    """Phase 2: answer_compose và rewrite_question có v2 đầy đủ metadata; render không thiếu biến."""
    from backend.infra.llm.prompt_registry import registry

    reg = registry()
    required_meta = ("name", "model", "owner", "created", "changelog")

    for name in ("answer_compose", "rewrite_question"):
        prompt = reg.get(name, version=2)
        assert prompt.version == 2, f"{name} v2.version phải là 2"
        assert prompt.template.strip(), f"{name} v2 template rỗng"
        for field in required_meta:
            assert getattr(prompt, field, "").strip(), f"{name} v2 thiếu metadata '{field}'"

    answer_rendered = reg.render(
        "answer_compose",
        version=2,
        question="Giá FPT?",
        symbol="FPT",
        price_summary="FPT: 95000 VND",
        news_summary="(không có tin)",
        eval_summary="(không)",
        evidence="FPT close=95000",
        violations="(không)",
    )
    assert "FPT" in answer_rendered
    assert "grounding" in answer_rendered.lower() or "evidence" in answer_rendered.lower()

    rewrite_rendered = reg.render(
        "rewrite_question",
        version=2,
        question="Tại sao lại giảm?",
        conversation='[{"role":"user","content":"Giá FPT hôm nay?"}]',
    )
    assert "Tại sao lại giảm?" in rewrite_rendered
    assert "Turn 2" in rewrite_rendered or "đại từ" in rewrite_rendered


def test_phase2_production_still_points_to_v1():
    """Phase 2: production.txt chưa promote v2 — production vẫn dùng template v1."""
    from backend.infra.llm.prompt_registry import registry

    reg = registry()
    for name in ("answer_compose", "rewrite_question"):
        prod = reg.get(name, version="production")
        v1 = reg.get(name, version=1)
        assert prod.template.strip() == v1.template.strip(), (
            f"{name}: production phải giữ template v1 (chưa promote v2)"
        )
        v2 = reg.get(name, version=2)
        assert v2.template.strip() != v1.template.strip(), (
            f"{name}: v2 phải khác v1 để git diff có ý nghĩa"
        )


# ==============================================================================
# Exact cache — Phase 8 (M3-B3)
# ==============================================================================


def test_exact_cache_key_includes_prompt_version():
    """Cache key phải đổi khi bump prompt_version."""
    from backend.infra.cache.exact import ExactCache, normalize_question

    cache = ExactCache()
    q = normalize_question("Giá FPT hôm nay?")
    k_prod = cache.make_key("answer_compose", "production", "gpt-4o-mini", q)
    k_v2 = cache.make_key("answer_compose", "2", "gpt-4o-mini", q)
    assert k_prod != k_v2


def test_exact_cache_hit_on_repeat_question(monkeypatch):
    """Cùng câu hỏi 2 lần → lần 2 cache_hit=true, không gọi API lần 2."""
    from backend.infra.cache.exact import (
        clear_llm_cache_context,
        get_exact_cache,
        set_llm_cache_context,
    )
    from backend.infra.cache.semantic import get_semantic_cache
    from backend.infra.cost.tracker import get_cost_tracker, reset_cost_tracker
    from backend.infra.llm import completion as completion_mod

    get_exact_cache().clear()
    get_semantic_cache().clear()
    reset_cost_tracker()
    calls: list[int] = []

    class _Usage:
        prompt_tokens = 100
        completion_tokens = 50
        total_tokens = 150

    def fake_create(**kwargs):
        calls.append(1)
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock(message=MagicMock(content="cached answer"))]
        mock_resp.usage = _Usage()
        return mock_resp

    fake_client = MagicMock()
    fake_client.chat.completions.create = fake_create
    monkeypatch.setattr(completion_mod, "get_client", lambda: fake_client)
    monkeypatch.setattr("backend.infra.llm.client.get_client", lambda: fake_client)
    monkeypatch.setattr(completion_mod, "retry_with_backoff", lambda fn, **kw: fn())
    monkeypatch.setenv("EXACT_CACHE_ENABLED", "true")

    messages = [{"role": "user", "content": "test"}]
    set_llm_cache_context(
        prompt_name="answer_compose",
        prompt_version="production",
        normalized_question="Giá FPT hôm nay?",
    )
    assert completion_mod.chat(messages) == "cached answer"
    assert completion_mod.chat(messages) == "cached answer"
    clear_llm_cache_context()

    assert len(calls) == 1
    summary = get_cost_tracker().summary()
    assert summary["cache_hits"] == 1
    assert summary["requests"] == 2


def test_exact_cache_miss_on_prompt_version_bump(monkeypatch):
    """Bump prompt_version → cache miss, gọi API lại."""
    from backend.infra.cache.exact import (
        clear_llm_cache_context,
        get_exact_cache,
        set_llm_cache_context,
    )
    from backend.infra.cache.semantic import get_semantic_cache
    from backend.infra.llm import completion as completion_mod

    get_exact_cache().clear()
    get_semantic_cache().clear()
    calls: list[int] = []

    class _Usage:
        prompt_tokens = 80
        completion_tokens = 40
        total_tokens = 120

    def fake_create(**kwargs):
        calls.append(1)
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock(message=MagicMock(content=f"answer-{len(calls)}"))]
        mock_resp.usage = _Usage()
        return mock_resp

    fake_client = MagicMock()
    fake_client.chat.completions.create = fake_create
    monkeypatch.setattr(completion_mod, "get_client", lambda: fake_client)
    monkeypatch.setattr("backend.infra.llm.client.get_client", lambda: fake_client)
    monkeypatch.setattr(completion_mod, "retry_with_backoff", lambda fn, **kw: fn())
    monkeypatch.setenv("EXACT_CACHE_ENABLED", "true")

    messages = [{"role": "user", "content": "test"}]
    set_llm_cache_context(
        prompt_name="answer_compose",
        prompt_version="production",
        normalized_question="Giá FPT?",
    )
    first = completion_mod.chat(messages)
    set_llm_cache_context(
        prompt_name="answer_compose",
        prompt_version="2",
        normalized_question="Giá FPT?",
    )
    second = completion_mod.chat(messages)
    clear_llm_cache_context()

    assert len(calls) == 2
    assert first == "answer-1"
    assert second == "answer-2"


def test_cost_baseline_with_cache_tier1_dry_run(tmp_path):
    """cost_baseline --with-cache tier1 dry-run: pass 2 có cache hits."""
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from cost_baseline import run_baseline  # type: ignore

    md = tmp_path / "cost_tier1.md"
    js = tmp_path / "cost_tier1.json"
    payload = run_baseline(
        limit=5,
        dry_run=True,
        with_cache="tier1",
        output_md=md,
        output_json=js,
    )
    summary = payload["summary"]
    assert payload["passes"] == 2
    assert summary["cache_hits"] > 0
    assert summary["cache_hit_rate"] > 0


# ==============================================================================
# Semantic cache — Phase 9 (M3-B3)
# ==============================================================================


def test_semantic_cache_skips_dynamic_question():
    """Câu có ngày/giá động không dùng semantic cache."""
    from backend.infra.cache.semantic import SemanticCache, is_dynamic_question

    assert is_dynamic_question("Giá FPT hôm nay bao nhiêu?")
    assert is_dynamic_question("VNM 95000 VND")
    assert not is_dynamic_question("Tin FPT mới nhất")

    cache = SemanticCache()
    cache.store(
        prompt_name="answer_compose",
        prompt_version="production",
        model="gpt-4o-mini",
        question="Tin FPT mới nhất",
        value="answer-a",
    )
    hit = cache.lookup(
        prompt_name="answer_compose",
        prompt_version="production",
        model="gpt-4o-mini",
        question="Giá FPT hôm nay?",
    )
    assert hit is None


def test_semantic_cache_hit_paraphrase(monkeypatch):
    """Paraphrase gần nghĩa → semantic hit khi cosine ≥ 0.93."""
    from backend.infra.cache.exact import (
        clear_llm_cache_context,
        get_exact_cache,
        set_llm_cache_context,
    )
    from backend.infra.cache.semantic import get_semantic_cache, set_semantic_question
    from backend.infra.llm import completion as completion_mod

    shared_vec = [1.0] + [0.0] * 255
    monkeypatch.setattr(
        "backend.infra.cache.semantic.embed_question",
        lambda _text: list(shared_vec),
    )

    get_semantic_cache().clear()
    get_exact_cache().clear()
    calls: list[int] = []

    class _Usage:
        prompt_tokens = 90
        completion_tokens = 30
        total_tokens = 120

    def fake_create(**kwargs):
        calls.append(1)
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock(message=MagicMock(content="tin fpt answer"))]
        mock_resp.usage = _Usage()
        return mock_resp

    fake_client = MagicMock()
    fake_client.chat.completions.create = fake_create
    monkeypatch.setattr(completion_mod, "get_client", lambda: fake_client)
    monkeypatch.setattr("backend.infra.llm.client.get_client", lambda: fake_client)
    monkeypatch.setattr(completion_mod, "retry_with_backoff", lambda fn, **kw: fn())
    monkeypatch.setenv("EXACT_CACHE_ENABLED", "true")
    monkeypatch.setenv("SEMANTIC_CACHE_ENABLED", "true")

    messages = [{"role": "user", "content": "test"}]
    set_llm_cache_context(
        prompt_name="answer_compose",
        prompt_version="production",
        normalized_question="tin tuc ve fpt",
    )
    set_semantic_question("tin tuc ve fpt")
    completion_mod.chat(messages)

    set_llm_cache_context(
        prompt_name="answer_compose",
        prompt_version="production",
        normalized_question="tin fpt",
    )
    set_semantic_question("tin fpt")
    out = completion_mod.chat(messages)
    clear_llm_cache_context()

    assert out == "tin fpt answer"
    assert len(calls) == 1
    assert len(get_semantic_cache().audit_log) >= 1


def test_semantic_cache_below_threshold_miss(monkeypatch):
    """Cosine dưới ngưỡng → miss."""
    from backend.infra.cache.semantic import SemanticCache

    cache = SemanticCache(threshold=0.93)
    cache.store(
        prompt_name="answer_compose",
        prompt_version="production",
        model="gpt-4o-mini",
        question="giá cổ phiếu fpt",
        value="stored",
    )
    hit = cache.lookup(
        prompt_name="answer_compose",
        prompt_version="production",
        model="gpt-4o-mini",
        question="thời tiết hà nội",
    )
    assert hit is None


def test_cache_benchmark_dry_run(tmp_path):
    """cache_benchmark.py --dry-run tạo bảng 3 dòng."""
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from cache_benchmark import run_benchmark  # type: ignore

    md = tmp_path / "cache_benchmark.md"
    js = tmp_path / "cache_benchmark.json"
    payload = run_benchmark(
        limit=50,
        dry_run=True,
        output_md=md,
        output_json=js,
    )
    assert md.is_file()
    text = md.read_text(encoding="utf-8")
    assert "Không cache" in text
    assert "Chỉ tầng 1" in text
    assert "Tầng 1 + 2" in text
    modes = payload["modes"]
    assert modes["tier1_tier2"]["cache_hits"] > modes["none"]["cache_hits"]
