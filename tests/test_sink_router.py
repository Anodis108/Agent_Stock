"""SinkRouter (Router tầng 2) — quyết định dữ liệu trích xuất thuộc sink nào
(giá / tin theo mã / tin chung), theo Ý NGHĨA NGHIỆP VỤ chứ không phải loại nội dung."""

from __future__ import annotations

from vn_stock_swarm.fetcher import RawResponse
from vn_stock_swarm.router import RouteResult
from vn_stock_swarm.sink_router import SinkRouter


def _response(url: str = "https://cafef.vn/a", content_type: str = "text/html") -> RawResponse:
    return RawResponse(url=url, status_code=200, content_type=content_type, body=b"", text="")


def test_api_agent_source_always_routes_to_price() -> None:
    """Mọi kết quả từ ApiAgent, bất kể handler nào xử lý, luôn là dữ liệu giá
    trong phạm vi project này (API giá kiểu SSI/TCBS)."""
    router = SinkRouter()
    route_result = RouteResult(handler_name="json", metadata={"num_links": "0"})
    decision = router.route(_response(content_type="application/json"), route_result, "api")
    assert decision.sink == "price"


def test_json_handler_output_routes_to_price_regardless_of_source() -> None:
    """JsonHandler xử lý được nghĩa là response giống JSON — coi là giá dù
    nguồn không phải ApiAgent (vd Scout handoff sang rồi vẫn tự parse JSON)."""
    router = SinkRouter()
    route_result = RouteResult(handler_name="json")
    decision = router.route(_response(), route_result, "scout")
    assert decision.sink == "price"


def test_html_title_matching_known_symbol_routes_to_news_by_symbol() -> None:
    """Title khớp mã cổ phiếu đã biết → tin theo mã, kèm đúng mã đã khớp."""
    router = SinkRouter()
    route_result = RouteResult(handler_name="html", title="HPG bứt phá phiên sáng nay")
    decision = router.route(_response(), route_result, "scout")
    assert decision.sink == "news_by_symbol"
    assert decision.symbols == ["HPG"]


def test_html_title_matching_company_name_alias() -> None:
    """Khớp không chỉ mã mà cả bí danh tên công ty (vd "Vinamilk" → VNM)."""
    router = SinkRouter()
    route_result = RouteResult(
        handler_name="html", title="Vinamilk công bố kết quả kinh doanh quý 3"
    )
    decision = router.route(_response(), route_result, "scout")
    assert decision.sink == "news_by_symbol"
    assert decision.symbols == ["VNM"]


def test_html_title_with_no_known_symbol_falls_back_to_general() -> None:
    """Không khớp mã nào → tin chung, KHÔNG phải lỗi (vd tin vĩ mô)."""
    router = SinkRouter()
    route_result = RouteResult(handler_name="html", title="Ngân hàng Nhà nước điều chỉnh lãi suất")
    decision = router.route(_response(), route_result, "scout")
    assert decision.sink == "news_general"
    assert decision.symbols == []


def test_title_mentioning_multiple_symbols_matches_all() -> None:
    """1 bài nhắc nhiều mã (tin ngành) phải khớp được TẤT CẢ, không chỉ mã đầu tiên."""
    router = SinkRouter()
    route_result = RouteResult(handler_name="html", title="VNM và HPG cùng tăng điểm phiên hôm nay")
    decision = router.route(_response(), route_result, "scout")
    assert decision.sink == "news_by_symbol"
    assert set(decision.symbols) == {"VNM", "HPG"}
