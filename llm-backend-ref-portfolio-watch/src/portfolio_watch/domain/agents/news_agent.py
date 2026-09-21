"""Re-export news_agent — legacy path (Phase 12b → agents/news_agent/)."""

from src.portfolio_watch.agents.news_agent import (
    HeuristicNewsBrain,
    LlmNewsBrain,
    MAX_STEPS,
    NewsAgentBrain,
    NewsAgentResult,
    NewsReactAction,
    _DEFAULT_NEWS_BRAIN_FACTORY,
    default_news_brain,
    fetch_cafef_news,
    run_news_agent,
)

__all__ = [
    "HeuristicNewsBrain",
    "LlmNewsBrain",
    "MAX_STEPS",
    "NewsAgentBrain",
    "NewsAgentResult",
    "NewsReactAction",
    "_DEFAULT_NEWS_BRAIN_FACTORY",
    "default_news_brain",
    "fetch_cafef_news",
    "run_news_agent",
]
