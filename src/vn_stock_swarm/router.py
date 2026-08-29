"""Router pattern — tầng 1 (post-crawl): nhìn 1 RawResponse, phân loại theo
NỘI DUNG, định tuyến sang đúng 1 ContentHandler.

Khác với domain-ownership hashing của swarm (nơi mỗi agent tự quyết định
CÓ xử lý URL này hay không), router quyết định AI xử lý phần thân trang, cho
mọi response, một cách xác định (deterministic) và độc quyền (mỗi response
chỉ khớp đúng 1 handler). Đầu ra của nó (RouteResult) là hợp đồng ổn định mà
SinkRouter (tầng 2, xem sink_router.py) tiêu thụ để quyết định dữ liệu trích
xuất được LƯU Ở ĐÂU.
"""

from __future__ import annotations

import io
import json
from dataclasses import dataclass, field
from typing import Protocol
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from vn_stock_swarm.fetcher import RawResponse
from vn_stock_swarm.logging_config import get_logger

logger = get_logger(component="router")


@dataclass
class RouteResult:
    """Những gì 1 ContentHandler trích xuất được từ 1 RawResponse."""

    handler_name: str
    title: str = ""
    links: list[str] = field(default_factory=list)
    # URL mà handler coi là chính thống/giá trị cao (vd entry trong sitemap
    # hoặc feed) chứ không chỉ đơn thuần "được tham chiếu từ 1 trang". Agent
    # coi các URL này là seed mới tinh thay vì trừ vào ngân sách depth hiện tại.
    priority_links: list[str] = field(default_factory=list)
    extracted_text: str = ""
    metadata: dict[str, str] = field(default_factory=dict)


class ContentHandler(Protocol):
    name: str

    def matches(self, response: RawResponse) -> bool: ...

    def handle(self, response: RawResponse) -> RouteResult: ...


def _looks_like_xml_feed(text: str) -> bool:
    snippet = text[:500].lower()
    return any(tag in snippet for tag in ("<urlset", "<sitemapindex", "<rss", "<feed"))


class SitemapHandler:
    """Sitemap XML (<urlset>/<sitemapindex>) và feed RSS/Atom.

    Hai loại này được xử lý như nhau vì bản chất giống nhau — "chính site chủ
    động khai báo URL nào quan trọng" — dù cấu trúc XML khác nhau.
    """

    name = "sitemap"

    def matches(self, response: RawResponse) -> bool:
        if _looks_like_xml_feed(response.text):
            return True
        return "sitemap" in response.url.lower() and "xml" in response.content_type

    def handle(self, response: RawResponse) -> RouteResult:
        links: list[str] = []
        try:
            soup = BeautifulSoup(response.text, "xml")
            for loc in soup.find_all("loc"):
                if loc.string:
                    links.append(loc.string.strip())
            for link_tag in soup.find_all("link"):
                href = link_tag.get("href")
                if href:
                    links.append(href.strip())
                elif link_tag.string:
                    links.append(link_tag.string.strip())
        except Exception as exc:
            logger.warning("sitemap_parse_failed", url=response.url, error=str(exc))

        resolved = list(dict.fromkeys(urljoin(response.url, link) for link in links))
        return RouteResult(
            handler_name=self.name,
            priority_links=resolved,
            metadata={"num_entries": str(len(resolved))},
        )


class PdfHandler:
    """Tài liệu PDF — chỉ trích text, không cố tìm link bên trong."""

    name = "pdf"

    def matches(self, response: RawResponse) -> bool:
        if response.content_type == "application/pdf":
            return True
        if response.url.lower().split("?")[0].endswith(".pdf"):
            return True
        return response.body[:5] == b"%PDF-"

    def handle(self, response: RawResponse) -> RouteResult:
        text, num_pages = "", 0
        try:
            reader = PdfReader(io.BytesIO(response.body))
            num_pages = len(reader.pages)
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
        except (PdfReadError, ValueError, TypeError) as exc:
            logger.warning("pdf_parse_failed", url=response.url, error=str(exc))

        return RouteResult(
            handler_name=self.name,
            extracted_text=text,
            metadata={"num_pages": str(num_pages)},
        )


class JsonHandler:
    """Response JSON của API — duyệt cấu trúc tìm chuỗi giống URL để có thể đi
    tiếp theo trang (pagination: ``next``, ``next_page``, ...) mà không cần
    biết trước schema của bất kỳ API cụ thể nào."""

    name = "json"
    _URL_LIKE_KEYS = {"url", "href", "link", "next", "next_page", "nextpage", "nexturl"}
    _MAX_DEPTH = 20

    def matches(self, response: RawResponse) -> bool:
        if "json" in response.content_type:
            return True
        stripped = response.text.lstrip()
        return stripped.startswith("{") or stripped.startswith("[")

    def handle(self, response: RawResponse) -> RouteResult:
        links: list[str] = []
        try:
            data = json.loads(response.text)
            self._collect(data, links)
        except (json.JSONDecodeError, RecursionError) as exc:
            logger.warning("json_parse_failed", url=response.url, error=str(exc))

        resolved = list(dict.fromkeys(urljoin(response.url, link) for link in links))
        return RouteResult(
            handler_name=self.name, links=resolved, metadata={"num_links": str(len(resolved))}
        )

    def _collect(self, node: object, out: list[str], depth: int = 0) -> None:
        if depth > self._MAX_DEPTH:
            return
        if isinstance(node, dict):
            for key, value in node.items():
                if isinstance(value, str) and (
                    key.lower() in self._URL_LIKE_KEYS or value.startswith(("http://", "https://"))
                ):
                    out.append(value)
                else:
                    self._collect(value, out, depth + 1)
        elif isinstance(node, list):
            for item in node:
                self._collect(item, out, depth + 1)
        elif isinstance(node, str) and node.startswith(("http://", "https://")):
            out.append(node)


class HtmlHandler:
    """Trang HTML thông thường — hành vi crawler nguyên bản."""

    name = "html"

    def matches(self, response: RawResponse) -> bool:
        return "html" in response.content_type

    def handle(self, response: RawResponse) -> RouteResult:
        soup = BeautifulSoup(response.text, "lxml")
        title = soup.title.string.strip() if soup.title and soup.title.string else ""

        links: list[str] = []
        for anchor in soup.find_all("a", href=True):
            absolute = urljoin(response.url, anchor["href"])
            parsed = urlparse(absolute)
            if parsed.scheme in ("http", "https"):
                links.append(absolute.split("#")[0])

        return RouteResult(handler_name=self.name, title=title, links=links)


class BinaryHandler:
    """Handler bắt-tất-cả cho phần còn lại (ảnh, video, file nén, ...) — chỉ
    ghi metadata, không cố trích link hay text. Luôn khớp, nên phải đăng ký
    CUỐI CÙNG trong router để làm fallback vô điều kiện."""

    name = "binary"

    def matches(self, response: RawResponse) -> bool:
        return True

    def handle(self, response: RawResponse) -> RouteResult:
        return RouteResult(
            handler_name=self.name,
            metadata={"content_type": response.content_type, "size_bytes": str(len(response.body))},
        )


def default_handlers() -> list[ContentHandler]:
    """Thứ tự có ý nghĩa: handler càng đặc thù đứng càng trước, BinaryHandler
    luôn ở cuối làm fallback vô điều kiện."""
    return [
        SitemapHandler(),
        PdfHandler(),
        JsonHandler(),
        HtmlHandler(),
        BinaryHandler(),
    ]


class ContentRouter:
    """Soi 1 RawResponse và định tuyến nó tới đúng 1 ContentHandler.

    Đây là Router-pattern tầng 1 (post-crawl): khác với domain-ownership
    hashing của swarm (nơi mỗi agent tự quyết định CÓ xử lý hay không), router
    quyết định handler chuyên biệt nào parse phần thân, cho mọi response, một
    cách xác định và độc quyền. Đầu ra của nó (RouteResult) là hợp đồng ổn
    định mà SinkRouter (tầng 2, xem sink_router.py) tiêu thụ để quyết định dữ
    liệu trích xuất được LƯU vào đâu.
    """

    def __init__(self, handlers: list[ContentHandler] | None = None) -> None:
        self._handlers = handlers if handlers is not None else default_handlers()

    def route(self, response: RawResponse) -> RouteResult:
        for handler in self._handlers:
            if handler.matches(response):
                return handler.handle(response)
        # Không bao giờ chạy tới đây khi BinaryHandler (khớp mọi thứ) còn đăng
        # ký — giữ lại như lưới an toàn nếu ai đó truyền handler list tuỳ biến
        # mà quên BinaryHandler.
        return BinaryHandler().handle(response)
