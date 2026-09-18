"""Phase 4 — Frontend gọi Backend (static contract, không mock)."""

from __future__ import annotations

from pathlib import Path

FE = Path(__file__).resolve().parents[1] / "frontend"


def test_app_js_wires_four_api_groups():
    js = (FE / "app.js").read_text(encoding="utf-8")
    assert "MOCK_STEPS" not in js
    assert 'api("POST", "/chat"' in js or 'api("POST","/chat"' in js.replace(" ", "")
    assert "/scan" in js
    assert "/watchlist" in js
    assert "/approvals" in js
    assert "/approvals/" in js and "approve" in js and "reject" in js
    assert "PATCH" in js
    assert "PW_getBackendBaseUrl" in js
    # FE → Backend only
    assert "8001" not in js
    assert "AI_BASE_URL" not in js


def test_index_has_forms_for_watchlist_and_scan():
    html = (FE / "index.html").read_text(encoding="utf-8")
    assert 'id="watchlist-form"' in html
    assert 'id="watchlist-symbol"' in html
    assert 'id="scan-form"' in html
    assert 'id="scan-symbol"' in html
    assert 'id="chat-form"' in html
