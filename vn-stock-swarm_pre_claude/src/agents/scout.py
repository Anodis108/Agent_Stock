from __future__ import annotations

from agents.base import BaseCrawlerAgent


class ScoutAgent(BaseCrawlerAgent):
    """Agent mặc định — GET HTTP thuần cho trang HTML nhẹ (bảng giá + tin tức
    trên cafef.vn, vietstock.vn). Mọi URL mới đều được thử ở đây trước tiên,
    trừ khi pre_route.py đã định tuyến sang nơi khác; ScoutAgent handoff sang
    RenderAgent/DocumentAgent/ApiAgent/StealthAgent (xem handoff.py) bất cứ khi
    nào response thật không khớp với những gì 1 lượt GET thuần xử lý được.
    """

    agent_type = "scout"
