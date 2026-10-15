"""Trang chat giữ bộ chọn user và stream từng token. Không thêm màn hình."""

from pathlib import Path


def _frontend() -> Path:
    return Path(__file__).resolve().parents[2] / "src" / "frontend"


def test_web_entry_serves_one_chat_screen_with_three_users():
    """backend mở đúng một trang chat và bộ chọn User A, User B, Default."""
    from fastapi.testclient import TestClient

    from backend.main import app

    frontend = _frontend()
    assert [p.name for p in sorted(frontend.glob("*.html"))] == ["index.html"]

    client = TestClient(app)
    page = client.get("/")
    assert page.status_code == 200
    assert "text/html" in page.headers.get("content-type", "")
    assert 'id="chat-view"' in page.text
    assert 'id="user-switcher-select"' in page.text
    assert 'value="user_a"' in page.text and "User A" in page.text
    assert 'value="user_b"' in page.text and "User B" in page.text
    assert 'value="default"' in page.text and "Default" in page.text
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/health").json()["service"] in ("web", "backend")


def test_chat_page_keeps_user_switcher_and_token_stream():
    frontend = _frontend()
    html_files = sorted(frontend.glob("*.html"))
    assert [p.name for p in html_files] == ["index.html"]

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
    assert 'fetch(apiUrl("/chat")' in script
    assert '"Accept": "text/event-stream"' in script
    assert '"X-User-ID": getCurrentUserId()' in script
    assert 'eventName === "token"' in script
    assert "streamedText += delta" in script
    assert "textEl.textContent = streamedText" in script


def test_token_events_fill_the_existing_chat_frame():
    """Sự kiện token ghi vào bong bóng trong #chat-messages, không mở màn khác."""
    frontend = _frontend()
    assert [p.name for p in sorted(frontend.glob("*.html"))] == ["index.html"]
    html = (frontend / "index.html").read_text(encoding="utf-8")
    script = (frontend / "app.js").read_text(encoding="utf-8")
    assert 'id="chat-messages"' in html
    assert "function getOrCreateStreamingMessage" in script
    assert 'document.getElementById("chat-messages")' in script
    assert 'streamingMsgDiv.className = "chat-msg chat-assistant chat-streaming"' in script
    assert "box.appendChild(streamingMsgDiv)" in script
    assert 'eventName === "token"' in script
    assert "streamedText += delta" in script
    assert "textEl.textContent = streamedText" in script


def test_source_file_and_feedback_stay_beside_the_answer():
    """Tên file nguồn và các nút cũ nằm trong cùng bong bóng với câu trả lời."""
    frontend = _frontend()
    assert [p.name for p in sorted(frontend.glob("*.html"))] == ["index.html"]
    script = (frontend / "app.js").read_text(encoding="utf-8")
    css = (frontend / "style.css").read_text(encoding="utf-8")
    fn = script[script.index("function appendChat") : script.index("async function doChat")]
    text_at = fn.index("body.appendChild(textNode)")
    source_at = fn.index("body.appendChild(sourceNode)")
    feedback_at = fn.index("body.appendChild(feedbackComp)")
    assert text_at < source_at < feedback_at
    assert 'sourceNode.textContent = "Nguồn: " + sourceName' in fn
    assert "createHitlFeedbackComponent(messageId, sessionId || currentSessionId)" in fn
    assert 'btnUp.innerHTML = "<span>👍</span>"' in script
    assert 'btnDown.innerHTML = "<span>👎</span>"' in script
    assert '{ id: "copied", label: "Đã copy" }' in script
    assert '{ id: "regenerated", label: "Hỏi lại" }' in script
    assert '{ id: "abandoned", label: "Bỏ dở" }' in script
    assert ".msg-source" in css
    assert ".hitl-feedback-container" in css


def test_concept_answer_shows_source_filename_in_existing_chat():
    script = (_frontend() / "app.js").read_text(encoding="utf-8")
    css = (_frontend() / "style.css").read_text(encoding="utf-8")
    assert "function conceptSourceName" in script
    assert "data.source_file" in script
    assert "m.source_file" in script
    assert 'sourceNode.className = "msg-source"' in script
    assert 'sourceNode.textContent = "Nguồn: " + sourceName' in script
    assert ".msg-source" in css


def test_answer_keeps_feedback_buttons_beside_the_text():
    script = (_frontend() / "app.js").read_text(encoding="utf-8")
    assert "createHitlFeedbackComponent(messageId, sessionId || currentSessionId)" in script
    assert "body.appendChild(feedbackComp)" in script
    assert 'btnUp.innerHTML = "<span>👍</span>"' in script
    assert 'btnDown.innerHTML = "<span>👎</span>"' in script
    assert '{ id: "copied", label: "Đã copy" }' in script
    assert '{ id: "regenerated", label: "Hỏi lại" }' in script
    assert '{ id: "abandoned", label: "Bỏ dở" }' in script
    assert 'reason: "thumbs_up"' in script
    assert 'reason: "thumbs_down"' in script
