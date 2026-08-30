from __future__ import annotations

from agents.api import ApiAgent
from agents.base import BaseCrawlerAgent
from agents.document import DocumentAgent
from agents.render import RenderAgent
from agents.scout import ScoutAgent
from agents.stealth import StealthAgent

AGENT_CLASSES: dict[str, type[BaseCrawlerAgent]] = {
    "scout": ScoutAgent,
    "render": RenderAgent,
    "document": DocumentAgent,
    "api": ApiAgent,
    "stealth": StealthAgent,
}

__all__ = [
    "AGENT_CLASSES",
    "ApiAgent",
    "BaseCrawlerAgent",
    "DocumentAgent",
    "RenderAgent",
    "ScoutAgent",
    "StealthAgent",
]
