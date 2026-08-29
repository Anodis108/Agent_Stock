from __future__ import annotations

from vn_stock_swarm.agents.api import ApiAgent
from vn_stock_swarm.agents.base import BaseCrawlerAgent
from vn_stock_swarm.agents.document import DocumentAgent
from vn_stock_swarm.agents.render import RenderAgent
from vn_stock_swarm.agents.scout import ScoutAgent
from vn_stock_swarm.agents.stealth import StealthAgent

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
