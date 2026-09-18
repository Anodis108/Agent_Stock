"""Phase 2 — frontend static server mở được UI (độc lập AI/Backend)."""

from __future__ import annotations

import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen

FE = Path(__file__).resolve().parents[1] / "frontend"
PORT = 5173


def test_frontend_static_server_serves_ui():
    """Chạy http.server trong process test — GET / trả HTML đủ section."""
    handler = partial(SimpleHTTPRequestHandler, directory=str(FE))
    # port 0 = OS chọn cổng trống (tránh đụng server đang chạy 5173)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        with urlopen(f"http://127.0.0.1:{port}/", timeout=5) as resp:
            assert resp.status == 200
            body = resp.read().decode("utf-8", errors="replace")
        assert "Portfolio Watch" in body
        assert 'id="chat"' in body
        assert 'id="timeline"' in body
        assert 'id="watchlist"' in body
        assert 'id="approvals"' in body
        assert "config.js" in body and "app.js" in body

        with urlopen(f"http://127.0.0.1:{port}/config.js", timeout=5) as resp:
            assert resp.status == 200
            cfg = resp.read().decode("utf-8", errors="replace")
        assert "BACKEND_BASE_URL" in cfg

        with urlopen(f"http://127.0.0.1:{port}/app.js", timeout=5) as resp:
            assert resp.status == 200
            js = resp.read()
            assert b"MOCK_STEPS" not in js
            assert b"/chat" in js and b"/watchlist" in js
            assert b"fetch" in js
    finally:
        httpd.shutdown()
