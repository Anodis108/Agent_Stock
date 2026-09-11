"""Router pattern — tầng 2 (post-crawl, sau ContentRouter): quyết định dữ liệu
trích xuất thuộc SINK nào (bảng lưu trữ nào), theo Ý NGHĨA NGHIỆP VỤ.

ContentRouter (tầng 1) đã quyết định xong "đây là loại nội dung gì" (html/
json/pdf/...). SinkRouter (tầng 2) trả lời 1 câu hỏi mà ContentRouter không hề
quan tâm: "item này thuộc CSDL nào?" — 2 kết quả cùng là "html" có thể là 1
bảng giá và 1 bài báo, và cần 2 nơi lưu khác nhau.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from fetcher import RawResponse
from router import RouteResult
from stock_symbols import match_symbols

Sink = Literal["price", "news_by_symbol", "news_general"]


@dataclass
class SinkDecision:
    """SinkRouter cho rằng dữ liệu trích xuất từ 1 RouteResult nên vào đâu."""

    sink: Sink
    symbols: list[str] = field(default_factory=list)


class SinkRouter:
    """Response từ ApiAgent luôn là dữ liệu giá trong phạm vi project này
    (API giá kiểu SSI/TCBS JSON — xem README về giả định nguồn dữ liệu). Mọi
    thứ còn lại giống 1 trang nội dung thông thường (có title) được coi là bài
    báo và khớp từ khoá với danh sách mã đã biết; 1 trang không khớp mã nào
    không phải lỗi — đó là tin vĩ mô/tin chung.
    """

    def route(
        self, response: RawResponse, route_result: RouteResult, source_agent_type: str
    ) -> SinkDecision:
        if source_agent_type == "api" or route_result.handler_name == "json":
            return SinkDecision(sink="price")

        symbols = match_symbols(route_result.title)
        if symbols:
            # "news_by_symbol" ở đây chỉ là NHÃN phân loại — nơi thực sự ghi
            # dữ liệu (news_pending, không phải news) do BaseCrawlerAgent
            # quyết định, vì SinkRouter chỉ phân loại, không tự ý biết về
            # khái niệm HITL của tầng Hierarchical (xem sink_store.py).
            return SinkDecision(sink="news_by_symbol", symbols=symbols)
        return SinkDecision(sink="news_general")
