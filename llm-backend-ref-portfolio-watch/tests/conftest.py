"""Pytest fixtures — giữ test deterministic khi Phase 8 bật LLM mặc định."""

from __future__ import annotations

import pytest

from src.portfolio_watch.domain.agents.answer_composer import HeuristicAnswerDraftBrain
from src.portfolio_watch.domain.agents.event_classifier import HeuristicEventClassifier
from src.portfolio_watch.domain.agents.eval_agent import HeuristicEvalBrain
from src.portfolio_watch.domain.agents.news_agent import HeuristicNewsBrain
from src.portfolio_watch.domain.agents.supervisor import (
    HeuristicRewriteBrain,
    HeuristicSupervisorBrain,
)
from src.portfolio_watch.domain.agents.synthesis_agent import HeuristicAlertComposer


@pytest.fixture(autouse=True)
def _use_heuristic_brains_in_tests(monkeypatch: pytest.MonkeyPatch):
    """Production mặc định = LLM brains; trong pytest dùng Heuristic để
    không gọi OpenAI / flake. Test LLM inject `brain=Llm*(chat_fn=...)`
    tường minh → không bị ảnh hưởng.
    """
    monkeypatch.setattr(
        "src.portfolio_watch.domain.agents.event_classifier._DEFAULT_BRAIN_FACTORY",
        HeuristicEventClassifier,
    )
    monkeypatch.setattr(
        "src.portfolio_watch.domain.agents.news_agent._DEFAULT_NEWS_BRAIN_FACTORY",
        HeuristicNewsBrain,
    )
    monkeypatch.setattr(
        "src.portfolio_watch.domain.agents.eval_agent._DEFAULT_EVAL_BRAIN_FACTORY",
        HeuristicEvalBrain,
    )
    monkeypatch.setattr(
        "src.portfolio_watch.domain.agents.synthesis_agent._DEFAULT_COMPOSER_FACTORY",
        HeuristicAlertComposer,
    )
    monkeypatch.setattr(
        "src.portfolio_watch.domain.agents.supervisor._DEFAULT_REWRITE_FACTORY",
        HeuristicRewriteBrain,
    )
    monkeypatch.setattr(
        "src.portfolio_watch.domain.agents.supervisor._DEFAULT_SUPERVISOR_FACTORY",
        HeuristicSupervisorBrain,
    )
    monkeypatch.setattr(
        "src.portfolio_watch.domain.agents.answer_composer._DEFAULT_ANSWER_BRAIN_FACTORY",
        HeuristicAnswerDraftBrain,
    )
