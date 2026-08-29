"""Tiện ích xử lý URL dùng chung — trích domain đã đăng ký và origin."""

from __future__ import annotations

from urllib.parse import urlparse

import tldextract

# suffix_list_urls=() ghim tldextract vào snapshot public-suffix đóng gói sẵn
# thay vì tải bản cập nhật qua mạng ở lần dùng đầu tiên — giữ hành vi xác định
# (deterministic) và chạy được offline (quan trọng cho test / môi trường không mạng).
_extractor = tldextract.TLDExtract(suffix_list_urls=())


def registered_domain(url: str) -> str:
    """Domain đã đăng ký, dùng để tính chủ sở hữu (hashing) / rate limit / cache robots.

    Ví dụ: https://blog.cafef.vn/path -> "cafef.vn"
    """
    ext = _extractor(url)
    return ".".join(part for part in (ext.domain, ext.suffix) if part)


def origin(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"
