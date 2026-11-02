"""Trang chat giữ bộ chọn user và stream từng token cho Web Backend."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from web_backend.main import app


def _find_frontend_dir() -> Path:
    candidates = [
        Path(__file__).resolve().parents[2] / "frontend",
        Path(__file__).resolve().parents[3] / "src" / "frontend",
        Path.cwd() / "src" / "frontend",
        Path.cwd() / "frontend",
    ]
    for c in candidates:
        if c.is_dir() and (c / "index.html").is_file():
            return c
    return Path(__file__).resolve().parents[3] / "src" / "frontend"


def test_web_entry_serves_one_chat_screen_with_three_users():
    """Web Backend phục vụ đúng một trang chat và bộ chọn User A, User B, Default."""
    frontend = _find_frontend_dir()
    html_files = [p.name for p in sorted(frontend.glob("*.html"))]
    assert "index.html" in html_files

    client = TestClient(app)
    page = client.get("/")
    assert page.status_code == 200
    assert "text/html" in page.headers.get("content-type", "").lower()
    assert 'id="chat-view"' in page.text
    assert 'id="user-switcher-select"' in page.text
    assert 'value="user_a"' in page.text and "User A" in page.text
    assert 'value="user_b"' in page.text and "User B" in page.text
    assert 'value="default"' in page.text and "Default" in page.text

    health = client.get("/health").json()
    assert health["status"] == "ok"
    assert health["service"] in ("web", "backend", "web_backend")


def test_chat_page_keeps_user_switcher_and_token_stream():
    """Kiểm tra mã nguồn frontend tích hợp SSE streaming và chuyển đổi user."""
    frontend = _find_frontend_dir()
    html = (frontend / "index.html").read_text(encoding="utf-8")
    assert 'id="chat-view"' in html
    assert 'id="user-switcher-select"' in html
    assert 'value="user_a"' in html
    assert "User A" in html
    assert 'value="user_b"' in html
    assert "User B" in html
    assert 'value="default"' in html
    assert "Default" in html

    script = (frontend / "app.js").read_text(encoding="utf-8")
    assert 'fetch(apiUrl("/chat")' in script or "fetch(" in script
    assert '"Accept": "text/event-stream"' in script or "text/event-stream" in script
    assert "token" in script
    assert "streamedText" in script or "textContent" in script


def test_token_events_fill_the_existing_chat_frame():
    """Sự kiện token ghi vào bong bóng trong #chat-messages, không mở màn khác."""
    frontend = _find_frontend_dir()
    html = (frontend / "index.html").read_text(encoding="utf-8")
    script = (frontend / "app.js").read_text(encoding="utf-8")

    assert 'id="chat-messages"' in html
    assert "chat-messages" in script
    assert "token" in script
