"""Phase 2 — frontend scaffold HTML/JS tồn tại."""

from __future__ import annotations

from pathlib import Path

FE = Path(__file__).resolve().parents[1] / "frontend"


def test_frontend_scaffold_files_exist():
    for name in ("index.html", "app.js", "style.css", "config.js", "README.md"):
        assert (FE / name).is_file(), f"missing frontend/{name}"


def test_frontend_readme_records_html_js_stack():
    text = (FE / "README.md").read_text(encoding="utf-8")
    assert "HTML" in text and "JS" in text
    assert "5173" in text
    assert "BACKEND_BASE_URL" in text


def test_frontend_index_loads_scripts():
    html = (FE / "index.html").read_text(encoding="utf-8")
    assert "config.js" in html
    assert "app.js" in html
    assert "style.css" in html


def test_frontend_main_page_has_four_sections():
    """Phase 2: chat + timeline + watchlist + approvals."""
    html = (FE / "index.html").read_text(encoding="utf-8")
    for section_id in ("chat", "timeline", "watchlist", "approvals"):
        assert f'id="{section_id}"' in html
    assert 'id="chat-input"' in html
    assert 'id="chat-form"' in html
    assert 'id="timeline-steps"' in html
    assert 'id="watchlist-body"' in html
    assert 'id="approvals-list"' in html
    assert "Timeline bước" in html or "timeline" in html.lower()


def test_frontend_calls_backend_not_mock():
    """Phase 4: FE gọi Backend chat/scan/watchlist/approvals — bỏ MOCK_STEPS."""
    js = (FE / "app.js").read_text(encoding="utf-8")
    assert "MOCK_STEPS" not in js
    assert "renderTimeline" in js or "PW_renderTimeline" in js
    for path in ("/chat", "/scan", "/watchlist", "/approvals"):
        assert path in js
    assert "fetch(" in js or "fetch (" in js
    assert "PW_getBackendBaseUrl" in js
    # Không gọi AI thẳng
    assert "8001" not in js
    assert "/v1/chat" not in js
    css = (FE / "style.css").read_text(encoding="utf-8")
    for status in ("pending", "running", "done", "error"):
        assert f"status-{status}" in css
    html = (FE / "index.html").read_text(encoding="utf-8")
    assert 'id="watchlist-form"' in html
    assert 'id="scan-form"' in html


def test_frontend_backend_base_url_config():
    """Phase 2: BACKEND_BASE_URL qua config.js + PW_getBackendBaseUrl."""
    cfg = (FE / "config.js").read_text(encoding="utf-8")
    assert "BACKEND_BASE_URL" in cfg
    assert "http://127.0.0.1:8000" in cfg
    assert "PW_getBackendBaseUrl" in cfg
    assert "backend" in cfg  # query override
    html = (FE / "index.html").read_text(encoding="utf-8")
    assert 'id="backend-url-display"' in html
    app = (FE / "app.js").read_text(encoding="utf-8")
    assert "PW_getBackendBaseUrl" in app
    readme = (FE / "README.md").read_text(encoding="utf-8")
    assert "BACKEND_BASE_URL" in readme
    assert "PW_getBackendBaseUrl" in readme
