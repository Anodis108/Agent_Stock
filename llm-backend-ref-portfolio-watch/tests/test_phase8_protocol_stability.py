"""Phase 8 — Protocol ổn định + application không hardcode Llm*.

Checklist: giữ Protocol; không đổi luồng gọi ở application/ (chỉ đổi
default bên trong agent qua factory).
"""

from __future__ import annotations

import ast
from pathlib import Path

from src.portfolio_watch.domain.agents.answer_composer import (
    AnswerDraftBrain,
    HeuristicAnswerDraftBrain,
    LlmAnswerDraftBrain,
    _DEFAULT_ANSWER_BRAIN_FACTORY,
)
from src.portfolio_watch.domain.agents.event_classifier import (
    EventClassifierBrain,
    HeuristicEventClassifier,
    LlmEventClassifier,
    _DEFAULT_BRAIN_FACTORY as _DEFAULT_CLASSIFIER_FACTORY,
)
from src.portfolio_watch.domain.agents.eval_agent import (
    EvalAgentBrain,
    HeuristicEvalBrain,
    LlmEvalBrain,
    _DEFAULT_EVAL_BRAIN_FACTORY,
)
from src.portfolio_watch.domain.agents.news_agent import (
    HeuristicNewsBrain,
    LlmNewsBrain,
    NewsAgentBrain,
    _DEFAULT_NEWS_BRAIN_FACTORY,
)
from src.portfolio_watch.domain.agents.supervisor import (
    HeuristicRewriteBrain,
    HeuristicSupervisorBrain,
    LlmRewriteBrain,
    LlmSupervisorBrain,
    RewriteBrain,
    SupervisorBrain,
    _DEFAULT_REWRITE_FACTORY,
    _DEFAULT_SUPERVISOR_FACTORY,
)
from src.portfolio_watch.domain.agents.synthesis_agent import (
    AlertComposer,
    HeuristicAlertComposer,
    LlmAlertComposer,
    _DEFAULT_COMPOSER_FACTORY,
)
from src.portfolio_watch.domain import ports as ports_mod

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "src" / "portfolio_watch" / "application"


def test_ports_core_protocols_still_present():
    """domain/ports.py — contract infra không bị đụng khi wire LLM agents."""
    for name in (
        "PriceSource",
        "NewsSource",
        "WatchlistStore",
        "PriceHistoryStore",
        "MemoryStore",
        "Notifier",
    ):
        assert hasattr(ports_mod, name), f"missing port {name}"


def test_agent_protocols_have_required_methods():
    specs = {
        EventClassifierBrain: ("classify",),
        NewsAgentBrain: ("decide", "filter_relevant"),
        EvalAgentBrain: ("needs_history", "build_severity"),
        AlertComposer: ("compose",),
        RewriteBrain: ("rewrite",),
        SupervisorBrain: ("route",),
        AnswerDraftBrain: ("compose",),
    }
    for proto, methods in specs.items():
        for method in methods:
            assert method in proto.__dict__, f"{proto.__name__}.{method}"


def test_llm_and_heuristic_implementations_expose_protocol_methods():
    pairs = [
        (LlmEventClassifier, HeuristicEventClassifier, ("classify",)),
        (LlmNewsBrain, HeuristicNewsBrain, ("decide", "filter_relevant")),
        (LlmEvalBrain, HeuristicEvalBrain, ("needs_history", "build_severity")),
        (LlmAlertComposer, HeuristicAlertComposer, ("compose",)),
        (LlmRewriteBrain, HeuristicRewriteBrain, ("rewrite",)),
        (LlmSupervisorBrain, HeuristicSupervisorBrain, ("route",)),
        (LlmAnswerDraftBrain, HeuristicAnswerDraftBrain, ("compose",)),
    ]
    for llm_cls, heur_cls, methods in pairs:
        for method in methods:
            assert callable(getattr(llm_cls, method)), f"{llm_cls.__name__}.{method}"
            assert callable(getattr(heur_cls, method)), f"{heur_cls.__name__}.{method}"


def test_production_defaults_are_llm_factories():
    assert _DEFAULT_CLASSIFIER_FACTORY is LlmEventClassifier
    assert _DEFAULT_NEWS_BRAIN_FACTORY is LlmNewsBrain
    assert _DEFAULT_EVAL_BRAIN_FACTORY is LlmEvalBrain
    assert _DEFAULT_COMPOSER_FACTORY is LlmAlertComposer
    assert _DEFAULT_REWRITE_FACTORY is LlmRewriteBrain
    assert _DEFAULT_SUPERVISOR_FACTORY is LlmSupervisorBrain
    assert _DEFAULT_ANSWER_BRAIN_FACTORY is LlmAnswerDraftBrain


def test_application_does_not_import_llm_brain_classes():
    """application/ chỉ inject optional brain — không import Llm* trực tiếp."""
    forbidden = {
        "LlmEventClassifier",
        "LlmNewsBrain",
        "LlmEvalBrain",
        "LlmAlertComposer",
        "LlmRewriteBrain",
        "LlmSupervisorBrain",
        "LlmAnswerDraftBrain",
    }
    for path in APP_DIR.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    assert alias.name not in forbidden, (
                        f"{path.name} imports {alias.name}"
                    )
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name not in forbidden


def test_application_still_passes_optional_brains_not_hardcoded_orchestration():
    """Luồng gọi vẫn nhận brain/composer optional — không ép Llm trong application."""
    scan = (APP_DIR / "scan_symbol.py").read_text(encoding="utf-8")
    answer = (APP_DIR / "answer_question.py").read_text(encoding="utf-8")
    assert "classifier_brain" in scan
    assert "eval_brain" in scan
    assert "alert_composer" in scan
    assert "default_news_brain()" in scan or "news_brain" in scan
    assert "rewrite_brain" in answer
    assert "supervisor_brain" in answer
    assert "answer_brain" in answer
    assert "eval_brain" in answer
    # Không hardcode class LLM trong application
    assert "Llm" not in scan
    assert "Llm" not in answer
