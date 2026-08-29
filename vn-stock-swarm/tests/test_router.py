"""ContentRouter (Router tầng 1) + từng ContentHandler — mỗi handler khớp
đúng 1 loại nội dung, BinaryHandler là fallback bắt-tất-cả."""

from __future__ import annotations

import io
import json

from pypdf import PdfWriter

from vn_stock_swarm.fetcher import RawResponse
from vn_stock_swarm.router import (
    BinaryHandler,
    ContentRouter,
    HtmlHandler,
    JsonHandler,
    PdfHandler,
    SitemapHandler,
)


def _response(
    url: str = "https://example.com/page",
    content_type: str = "text/html",
    text: str = "",
    body: bytes | None = None,
    status_code: int = 200,
) -> RawResponse:
    body_bytes = body if body is not None else text.encode("utf-8")
    return RawResponse(
        url=url, status_code=status_code, content_type=content_type, body=body_bytes, text=text
    )


# --- HtmlHandler -------------------------------------------------------------


def test_html_handler_matches_html_content_type() -> None:
    assert HtmlHandler().matches(_response(content_type="text/html"))


def test_html_handler_extracts_title_and_links() -> None:
    """Title phải được strip khoảng trắng thừa; link tương đối phải resolve
    thành tuyệt đối; link ngoài site vẫn giữ nguyên (không lọc theo domain)."""
    html = (
        "<html><head><title> My Page </title></head>"
        '<body><a href="/about">About</a><a href="https://other.com/x">X</a></body></html>'
    )
    result = HtmlHandler().handle(_response(url="https://example.com/", text=html))
    assert result.title == "My Page"
    assert "https://example.com/about" in result.links
    assert "https://other.com/x" in result.links


# --- SitemapHandler ------------------------------------------------------------


def test_sitemap_handler_matches_urlset_content() -> None:
    xml = "<?xml version='1.0'?><urlset><url><loc>https://example.com/a</loc></url></urlset>"
    assert SitemapHandler().matches(_response(content_type="application/xml", text=xml))


def test_sitemap_handler_extracts_locs() -> None:
    """URL trong sitemap phải là priority_links (seed mới, depth 0), không
    phải links thường (sẽ bị trừ vào ngân sách depth)."""
    xml = (
        "<?xml version='1.0'?><urlset>"
        "<url><loc>https://example.com/a</loc></url>"
        "<url><loc>https://example.com/b</loc></url>"
        "</urlset>"
    )
    result = SitemapHandler().handle(
        _response(url="https://example.com/sitemap.xml", content_type="application/xml", text=xml)
    )
    assert set(result.priority_links) == {"https://example.com/a", "https://example.com/b"}
    assert result.links == []


def test_sitemap_handler_extracts_rss_links() -> None:
    """SitemapHandler xử lý cả feed RSS/Atom giống sitemap XML — cùng ý nghĩa
    "site tự khai báo URL nào quan trọng"."""
    rss = (
        "<?xml version='1.0'?><rss><channel>"
        "<item><link>https://example.com/post-1</link></item>"
        "</channel></rss>"
    )
    result = SitemapHandler().handle(_response(url="https://example.com/feed.xml", text=rss))
    assert "https://example.com/post-1" in result.priority_links


# --- JsonHandler ---------------------------------------------------------------


def test_json_handler_matches_content_type() -> None:
    assert JsonHandler().matches(_response(content_type="application/json", text="{}"))


def test_json_handler_matches_sniffed_body_without_content_type() -> None:
    """Không có Content-Type JSON rõ ràng vẫn phải nhận ra được qua sniff body."""
    assert JsonHandler().matches(_response(content_type="text/plain", text='{"a": 1}'))


def test_json_handler_collects_pagination_and_url_values() -> None:
    """Phải gom được cả URL trong key gợi ý pagination (next) lẫn value bắt
    đầu bằng http(s), bỏ qua field không phải URL (note)."""
    payload = {
        "results": [{"url": "https://api.example.com/items/1"}],
        "next": "https://api.example.com/items?page=2",
        "note": "not a url",
    }
    result = JsonHandler().handle(
        _response(
            url="https://api.example.com/items",
            content_type="application/json",
            text=json.dumps(payload),
        )
    )
    assert "https://api.example.com/items/1" in result.links
    assert "https://api.example.com/items?page=2" in result.links
    assert len(result.links) == 2


def test_json_handler_handles_malformed_json_gracefully() -> None:
    """JSON hỏng không được làm crash agent — trả về links rỗng, chỉ log warning."""
    result = JsonHandler().handle(_response(content_type="application/json", text="{not valid"))
    assert result.links == []


# --- PdfHandler ------------------------------------------------------------------


def _make_pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def test_pdf_handler_matches_content_type() -> None:
    assert PdfHandler().matches(_response(content_type="application/pdf", body=b"%PDF-1.4 ..."))


def test_pdf_handler_matches_url_suffix() -> None:
    """Content-Type rỗng nhưng đuôi URL .pdf vẫn phải khớp — server đôi khi
    trả sai/thiếu Content-Type."""
    assert PdfHandler().matches(
        _response(url="https://example.com/doc.pdf", content_type="", body=b"%PDF-1.4 ...")
    )


def test_pdf_handler_extracts_page_count() -> None:
    result = PdfHandler().handle(
        _response(content_type="application/pdf", body=_make_pdf_bytes(), text="")
    )
    assert result.metadata["num_pages"] == "1"


def test_pdf_handler_survives_corrupt_pdf() -> None:
    """PDF hỏng không được làm crash agent — trả về text rỗng, num_pages=0, chỉ log warning."""
    result = PdfHandler().handle(
        _response(content_type="application/pdf", body=b"%PDF-not-really-a-pdf", text="")
    )
    assert result.extracted_text == ""
    assert result.metadata["num_pages"] == "0"


# --- BinaryHandler ---------------------------------------------------------------


def test_binary_handler_always_matches() -> None:
    """BinaryHandler là fallback vô điều kiện — phải khớp MỌI response."""
    assert BinaryHandler().matches(_response(content_type="image/png"))


def test_binary_handler_records_metadata() -> None:
    body = b"\x89PNG\r\n\x1a\n"
    result = BinaryHandler().handle(_response(content_type="image/png", body=body))
    assert result.metadata["content_type"] == "image/png"
    assert result.metadata["size_bytes"] == str(len(body))


# --- ContentRouter dispatch --------------------------------------------------------


def test_router_dispatches_html_by_default() -> None:
    router = ContentRouter()
    result = router.route(_response(content_type="text/html", text="<html></html>"))
    assert result.handler_name == "html"


def test_router_dispatches_sitemap_before_generic_xml() -> None:
    """Thứ tự handler có ý nghĩa: SitemapHandler (đặc thù hơn) phải được thử
    trước khi rơi vào các handler tổng quát hơn."""
    router = ContentRouter()
    xml = "<?xml version='1.0'?><urlset><url><loc>https://example.com/a</loc></url></urlset>"
    result = router.route(
        _response(url="https://example.com/sitemap.xml", content_type="application/xml", text=xml)
    )
    assert result.handler_name == "sitemap"


def test_router_falls_back_to_binary_for_unknown_content() -> None:
    router = ContentRouter()
    result = router.route(
        _response(content_type="application/octet-stream", body=b"\x00\x01\x02", text="")
    )
    assert result.handler_name == "binary"
