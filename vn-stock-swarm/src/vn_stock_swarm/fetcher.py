"""Fetch HTTP thô — chỉ lấy về, KHÔNG diễn giải nội dung."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from vn_stock_swarm.logging_config import get_logger

logger = get_logger(component="fetcher")

# Content-Type (hoặc mảnh của nó) đáng để decode ra text kể cả khi body lớn —
# bất cứ thứ gì dạng văn bản mà ContentHandler có thể cần soi/parse. Body thật
# sự nhị phân (ảnh, video, zip, ...) không decode trừ khi nhỏ, để không tốn CPU
# biến hàng megabyte nhị phân thành rác chỉ để kiểm tra vài byte đầu.
_TEXTUAL_HINTS = ("text", "xml", "json", "html")
_SMALL_BODY_THRESHOLD_BYTES = 65_536


@dataclass(frozen=True)
class RawResponse:
    """Kết quả tầng transport của việc fetch 1 URL — CỐ Ý chưa diễn giải gì.

    Biến kết quả này thành links / text trích xuất / metadata là việc của
    ContentRouter (xem router.py), không phải của fetcher. Tách fetch khỏi
    parse là điều cho phép router định tuyến mỗi response tới 1 handler khác
    nhau, có thể thay thế được, thay vì mọi response đều bị ép parse như HTML.

    RenderAgent dựng CÙNG dataclass này từ 1 trang đã render bằng Playwright
    (xem render_fetcher.py), nhờ vậy mọi thứ đọc kết quả — ContentRouter,
    SinkRouter, cơ chế phát hiện handoff — không cần biết fetcher nào đã tạo
    ra response.
    """

    url: str
    status_code: int
    content_type: str
    body: bytes
    text: str


async def fetch_page(client: httpx.AsyncClient, url: str) -> RawResponse | None:
    """Fetch ``url`` và trả về response thô, hoặc None nếu lỗi tầng transport
    (timeout, lỗi DNS, connection reset, ...)."""
    try:
        resp = await client.get(url, follow_redirects=True)
    except httpx.HTTPError as exc:
        logger.warning("fetch_failed", url=url, error=str(exc))
        return None

    content_type = resp.headers.get("content-type", "").split(";")[0].strip().lower()
    body = resp.content

    should_decode = (
        content_type == ""
        or any(hint in content_type for hint in _TEXTUAL_HINTS)
        or len(body) < _SMALL_BODY_THRESHOLD_BYTES
    )
    text = ""
    if should_decode:
        try:
            text = resp.text
        except UnicodeDecodeError:
            text = ""

    return RawResponse(
        url=str(resp.url),
        status_code=resp.status_code,
        content_type=content_type,
        body=body,
        text=text,
    )
