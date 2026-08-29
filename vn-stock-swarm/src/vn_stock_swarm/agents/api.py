from __future__ import annotations

from vn_stock_swarm.agents.base import BaseCrawlerAgent


class ApiAgent(BaseCrawlerAgent):
    """Agent chuyên JSON API — feed giá real-time kiểu SSI/TCBS, hiểu
    pagination qua JsonHandler của ContentRouter. Vào tới đây trực tiếp (path
    URL chứa /api/ hoặc đuôi .json) hoặc qua handoff từ ScoutAgent khi
    Content-Type thật hoá ra là JSON. SinkRouter coi MỌI kết quả từ ApiAgent
    là dữ liệu giá (xem sink_router.py) — phạm vi project này không bao gồm
    API JSON phi-giá.
    """

    agent_type = "api"
