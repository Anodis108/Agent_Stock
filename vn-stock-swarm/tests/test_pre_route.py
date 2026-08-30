"""guess_agent_type là định tuyến TRƯỚC-fetch (nét đứt cam, Sơ đồ 1) — chỉ
đoán từ hình dạng URL, chưa hề fetch trang."""

from __future__ import annotations

from pre_route import guess_agent_type, stream_name


def test_pdf_extension_routes_to_document() -> None:
    """Đuôi .pdf khớp thẳng vào DocumentAgent — không cần chờ handoff sau-fetch."""
    assert guess_agent_type("https://hnx.vn/reports/annual-2024.pdf") == "document"


def test_pdf_path_with_query_string_still_matches() -> None:
    """guess_agent_type kiểm tra urlparse(url).path — vốn đã loại bỏ query
    string — nên "?v=2" ở cuối không được làm hỏng kiểm tra đuôi .pdf."""
    assert guess_agent_type("https://ir.example.com/report.pdf?v=2") == "document"


def test_api_path_routes_to_api() -> None:
    """Path chứa /api/ khớp thẳng vào ApiAgent."""
    assert guess_agent_type("https://api.ssi.com.vn/api/v2/prices/HPG") == "api"


def test_json_extension_routes_to_api() -> None:
    """Đuôi .json cũng khớp vào ApiAgent, độc lập với kiểm tra path /api/."""
    assert guess_agent_type("https://data.tcbs.com.vn/prices/hpg.json") == "api"


def test_render_domain_whitelist_routes_to_render() -> None:
    """Domain đã biết trước là SPA nặng JS đi thẳng RenderAgent — không cần
    chờ ScoutAgent phát hiện shell rỗng rồi mới handoff."""
    assert guess_agent_type("https://iboard.ssi.com.vn/", render_domains=["ssi.com.vn"]) == "render"


def test_default_routes_to_scout() -> None:
    """Không khớp quy tắc nào ở trên thì mặc định vào ScoutAgent — cửa vào chung."""
    assert guess_agent_type("https://cafef.vn/thi-truong-chung-khoan.chn") == "scout"


def test_stream_name_is_namespaced_per_agent_type() -> None:
    """Mỗi loại agent phải có 1 stream gossip riêng — đây là điều cho phép 5
    loại agent không tranh nhau đọc message của nhau."""
    assert stream_name("scout") == "url:discovered:scout"
    assert stream_name("document") != stream_name("api")
