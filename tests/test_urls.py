"""Tiện ích URL dùng để tính chủ sở hữu domain (hashing) / rate limit / cache robots."""

from __future__ import annotations

from vn_stock_swarm.urls import origin, registered_domain


def test_registered_domain_strips_subdomain() -> None:
    """Subdomain phải bị loại — chủ sở hữu tính theo domain đã đăng ký, không
    theo từng subdomain riêng lẻ."""
    assert registered_domain("https://blog.example.co.uk/path") == "example.co.uk"


def test_registered_domain_simple() -> None:
    assert registered_domain("https://s.cafef.vn/") == "cafef.vn"


def test_origin_extracts_scheme_and_netloc() -> None:
    """origin() dùng để build URL robots.txt (origin + "/robots.txt")."""
    assert origin("https://example.com/a/b?c=1") == "https://example.com"
