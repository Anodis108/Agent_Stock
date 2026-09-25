"""NewsSource thật — CafeF Events_RelatedNews Ajax (HTML nhẹ, không API chính thức)."""

from __future__ import annotations

import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from html import unescape

from backend.domain.ports import NewsItem

# Host `s.cafef.vn/Ajax/...` trả ul rỗng; endpoint còn dữ liệu nằm dưới cafef.vn/du-lieu.
_CAFEF_NEWS_URL = (
    "https://cafef.vn/du-lieu/Ajax/Events_RelatedNews_New.aspx"
    "?symbol={symbol}&floorID=0&configID=0&PageIndex=1&PageSize={page_size}&Type=2"
)
_CAFEF_ORIGIN = "https://cafef.vn"

_LI_RE = re.compile(r"<li[^>]*>(.*?)</li>", re.I | re.S)
_SPAN_RE = re.compile(r"<span[^>]*>(.*?)</span>", re.I | re.S)
_A_RE = re.compile(
    r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.I | re.S
)
_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return unescape(_TAG_RE.sub("", text)).strip()


def _parse_cafef_html(html: str, symbol: str) -> list[NewsItem]:
    items: list[NewsItem] = []
    for block in _LI_RE.findall(html or ""):
        span = _SPAN_RE.search(block)
        link = _A_RE.search(block)
        if not link:
            continue
        href, title_html = link.group(1), link.group(2)
        title = _strip_html(title_html)
        if not title:
            continue
        published = _strip_html(span.group(1)) if span else None
        if href.startswith("//"):
            url = "https:" + href
        elif href.startswith("/"):
            url = _CAFEF_ORIGIN + href
        elif href.startswith("http"):
            url = href
        else:
            url = _CAFEF_ORIGIN + "/" + href.lstrip("/")
        items.append(
            NewsItem(
                title=title,
                url=url,
                published_at=published,
                snippet=title,
                symbol=symbol,
            )
        )
    return items


def _parse_cafef_date(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


class CafefNewsSource:
    """Lấy tin liên quan mã từ CafeF Ajax endpoint."""

    def __init__(self, timeout_seconds: float = 15.0, page_size: int = 30):
        self.timeout_seconds = timeout_seconds
        self.page_size = page_size

    def fetch_news(
        self,
        symbol: str,
        query: str | None = None,
        *,
        days: int | None = None,
    ) -> list[NewsItem]:
        sym = (symbol or "").strip().upper()
        if not sym:
            return []

        url = _CAFEF_NEWS_URL.format(
            symbol=urllib.parse.quote(sym),
            page_size=max(self.page_size, 1),
        )
        try:
            html = self._http_get(url)
        except Exception:
            # Để nguyên exception — NewsAgent gắn "không lấy được tin: …"
            raise

        items = _parse_cafef_html(html, sym)

        # CafeF endpoint đã lọc theo mã. Không lọc thêm theo `query` chữ trong
        # title — LLM NewsAgent hay search query dài ("tin VNM gần đây") → 0 tin.

        if days is not None and days > 0:
            cutoff = datetime.now() - timedelta(days=days)
            filtered: list[NewsItem] = []
            for item in items:
                published = _parse_cafef_date(item.published_at)
                if published is None or published >= cutoff:
                    filtered.append(item)
            items = filtered

        return items

    def _http_get(self, url: str) -> str:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; PortfolioWatch/0.1; +local-demo)"
                ),
                "Accept": "text/html,application/xhtml+xml",
                "Referer": f"{_CAFEF_ORIGIN}/",
            },
        )
        with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
            raw = resp.read()
        return raw.decode("utf-8", errors="replace")
