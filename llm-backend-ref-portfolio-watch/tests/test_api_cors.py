from __future__ import annotations

from fastapi.testclient import TestClient

from src.portfolio_watch.main import app

client = TestClient(app)

# 4 nhóm endpoint Phase 4 — web/app.js gọi cross-origin
_EXPECTED_METHODS = {
    "/scan": {"post"},
    "/chat": {"post"},
    "/approvals": {"get"},
    "/approvals/{approval_id}/approve": {"post"},
    "/approvals/{approval_id}/reject": {"post"},
    "/watchlist": {"get", "post"},
    "/watchlist/{symbol}": {"patch", "delete"},
    "/health": {"get"},
}


def test_all_routers_registered_with_methods():
    """Đăng ký đủ router + method khớp stub web/app.js."""
    paths = app.openapi()["paths"]
    for path, methods in _EXPECTED_METHODS.items():
        assert path in paths, f"thiếu path {path}"
        actual = {m.lower() for m in paths[path] if m.lower() != "parameters"}
        assert methods <= actual, f"{path}: cần {methods}, có {actual}"


def test_cors_allows_any_origin_on_api_endpoints():
    """Dev mọi origin — kể cả Live Server và file:// (Origin: null)."""
    for origin in (
        "http://127.0.0.1:5500",
        "http://localhost:3000",
        "null",
    ):
        for path in ("/health", "/watchlist", "/approvals"):
            resp = client.get(path, headers={"Origin": origin})
            assert resp.status_code == 200, path
            assert resp.headers.get("access-control-allow-origin") == "*"


def test_cors_preflight_for_web_mutations():
    """Preflight POST/PATCH/DELETE — web/ gửi Content-Type JSON."""
    cases = [
        ("/scan", "POST"),
        ("/chat", "POST"),
        ("/approvals/a1/approve", "POST"),
        ("/approvals/a1/reject", "POST"),
        ("/watchlist", "POST"),
        ("/watchlist/FPT", "PATCH"),
        ("/watchlist/FPT", "DELETE"),
    ]
    for path, method in cases:
        resp = client.options(
            path,
            headers={
                "Origin": "http://127.0.0.1:5500",
                "Access-Control-Request-Method": method,
                "Access-Control-Request-Headers": "content-type",
            },
        )
        assert resp.status_code in (200, 204), path
        assert resp.headers.get("access-control-allow-origin") == "*"
        allow = resp.headers.get("access-control-allow-methods", "")
        assert method in allow.upper() or allow == "*"
