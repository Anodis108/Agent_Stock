"""Tools news_agent — fetch tin CafeF qua NewsSource port."""

from __future__ import annotations

from src.portfolio_watch.domain.ports import NewsItem, NewsSource


def fetch_cafef_news(
    news_source: NewsSource,
    symbol: str,
    query: str,
    *,
    days: int | None = 7,
) -> list[NewsItem]:
    """Gọi `NewsSource.fetch_news` — tên tool khớp test-plan / agent_pr."""
    return news_source.fetch_news(symbol, query=query, days=days) or []
