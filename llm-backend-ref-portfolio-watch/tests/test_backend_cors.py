"""Phase 3b — Backend CORS theo FRONTEND_ORIGIN (dev có thể *)."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from backend.cors_util import resolve_cors_origins
from backend.main import app


def test_resolve_cors_origins_star_and_specific():
    assert resolve_cors_origins("*") == ["*"]
    assert resolve_cors_origins("  ") == ["*"]
    assert resolve_cors_origins(None) == ["*"]
    assert resolve_cors_origins("http://127.0.0.1:5173") == [
        "http://127.0.0.1:5173"
    ]


def test_backend_cors_allows_frontend_origin_on_get():
    """App đang chạy: reflect Origin nếu khớp FRONTEND_ORIGIN, hoặc * khi mở."""
    import os

    client = TestClient(app)
    configured = (os.environ.get("FRONTEND_ORIGIN") or "*").strip() or "*"
    for origin in (
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5500",
    ):
        resp = client.get("/health", headers={"Origin": origin})
        assert resp.status_code == 200
        allow = resp.headers.get("access-control-allow-origin")
        if configured == "*":
            assert allow == "*"
        elif origin == configured:
            assert allow == configured
        else:
            assert allow != origin


def test_backend_cors_preflight_chat_post():
    import os

    client = TestClient(app)
    configured = (os.environ.get("FRONTEND_ORIGIN") or "*").strip() or "*"
    origin = (
        configured
        if configured != "*"
        else "http://127.0.0.1:5173"
    )
    resp = client.options(
        "/chat",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert resp.status_code in (200, 204)
    allow = resp.headers.get("access-control-allow-origin")
    if configured == "*":
        assert allow == "*"
    else:
        assert allow == configured
    methods = resp.headers.get("access-control-allow-methods", "")
    assert "POST" in methods.upper() or methods == "*"


def test_cors_middleware_with_specific_origin():
    """Siết origin: chỉ FRONTEND_ORIGIN được reflect (không reload backend.main)."""
    mini = FastAPI()
    mini.add_middleware(
        CORSMiddleware,
        allow_origins=resolve_cors_origins("http://127.0.0.1:5173"),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @mini.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    client = TestClient(mini)
    ok = client.get("/health", headers={"Origin": "http://127.0.0.1:5173"})
    assert ok.status_code == 200
    assert ok.headers.get("access-control-allow-origin") == "http://127.0.0.1:5173"

    other = client.get("/health", headers={"Origin": "http://evil.example"})
    assert other.status_code == 200
    assert other.headers.get("access-control-allow-origin") != "http://evil.example"
