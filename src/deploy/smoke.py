#!/usr/bin/env python3
"""Smoke test sau deploy — Module III, Bài 6, Section 4 (Deployment Strategies).

Vì sao KHÔNG dùng "container đã start" làm tiêu chí deploy thành công:
    Một bản deploy hỏng rất nhiều kiểu mà `/health` vẫn trả 200 — model sai,
    hết quota API key, agent/chat lỗi chỉ lộ khi gọi thật. Container "healthy"
    chỉ nghĩa là process còn sống.

Nên smoke test phải đi hết một đường NGƯỜI DÙNG THẬT: health → hỏi 1 câu đã
biết kỳ vọng (FPT tăng/giảm hoặc từ chối hợp lệ) → (tuỳ chọn) SSE stream.

Đây là bước chặn cuối trong deploy.yml / cd.yml: smoke fail → rollback về
last-known-good, trước khi người dùng kịp thấy.

Khác llm-engineer-demo/deploy/smoke.py: demo còn bước ingest Qdrant rồi hỏi
câu pháp lý; swarm không ingest — dữ liệu giá/tin lấy runtime / fallback.

Chạy:
    python src/deploy/smoke.py --url http://localhost:8000
    python src/deploy/smoke.py --url http://localhost:8000 --stream
    python src/deploy/smoke.py --url https://<tunnel-or-ngrok> --stream
"""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request

# Câu smoke cố định — phải thấy tín hiệu về FPT/biến động hoặc từ chối phạm vi.
SMOKE_QUESTION = "FPT hôm nay tăng hay giảm?"
FPT_MARKERS = ("fpt", "tăng", "giảm", "biến động", "giá", "change")
REFUSAL_MARKERS = ("phạm vi", "không thể", "ngoài phạm vi", "từ chối", "sorry")


def _ascii_snippet(text: str, limit: int = 200) -> str:
    """Safe for Windows cp1252 consoles when printing API responses."""
    return (text or "")[:limit].encode("ascii", errors="replace").decode("ascii")


def _post_json(url: str, payload: dict) -> tuple[int, str]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as response:
        return response.getcode(), response.read().decode("utf-8", errors="replace")


def _answer_acceptable(text: str) -> bool:
    lower = (text or "").lower()
    if any(m in lower for m in FPT_MARKERS):
        return True
    return any(m in lower for m in REFUSAL_MARKERS)


def check_health(base_url: str) -> bool:
    print("--- Test 1: GET /health ---")
    url = f"{base_url}/health"
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            status_code = response.getcode()
            body = response.read().decode("utf-8", errors="replace")
            data = json.loads(body)
        if status_code == 200 and data.get("status") == "ok":
            print("PASS: /health -> status=ok")
            return True
        print(f"FAIL: /health -> {status_code} body={_ascii_snippet(body)}")
        return False
    except Exception as exc:
        print(f"FAIL: /health request error: {exc}")
        return False


def check_chat(base_url: str) -> bool:
    print("--- Test 2: POST /chat (FPT question) ---")
    url = f"{base_url}/chat"
    payload = {"question": SMOKE_QUESTION, "user_id": "smoke-test"}
    try:
        status_code, body = _post_json(url, payload)
        if status_code != 200:
            print(f"FAIL: POST /chat -> HTTP {status_code}")
            return False
        data = json.loads(body)
        answer = str(data.get("answer") or data.get("message") or "")
        if not _answer_acceptable(answer):
            print(f"FAIL: answer missing FPT/movement or valid refusal: {_ascii_snippet(answer)}")
            return False
        print(f"PASS: POST /chat -> 200, answer snippet: {_ascii_snippet(answer, 120)}...")
        return True
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace") if exc.fp else str(exc)
        print(f"FAIL: POST /chat -> HTTP {exc.code}: {_ascii_snippet(detail)}")
        return False
    except Exception as exc:
        print(f"FAIL: POST /chat request error: {exc}")
        return False


def check_stream(base_url: str) -> bool:
    print("--- Test 3: POST /api/v1/chat/stream (SSE) ---")
    url = f"{base_url}/api/v1/chat/stream"
    payload = {"question": SMOKE_QUESTION, "user_id": "smoke-test"}
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            if response.getcode() != 200:
                print(f"FAIL: stream -> HTTP {response.getcode()}")
                return False
            raw = response.read(65536).decode("utf-8", errors="replace")
        has_event = "event:" in raw
        has_data = "data:" in raw
        has_complete = "event: complete" in raw or "event:complete" in raw.replace(" ", "")
        has_token = "event: token" in raw or "event:token" in raw.replace(" ", "")
        if has_event and has_data and (has_complete or has_token):
            print("PASS: SSE stream has event + data + (complete|token)")
            return True
        print(f"FAIL: SSE missing expected event. snippet: {_ascii_snippet(raw, 300)}")
        return False
    except Exception as exc:
        print(f"FAIL: stream request error: {exc}")
        return False


def run_smoke(base_url: str, *, check_stream_flag: bool = False) -> int:
    base = base_url.rstrip("/")
    print(f"Smoke test -> {base}")

    ok = check_health(base)
    ok = check_chat(base) and ok
    if check_stream_flag:
        ok = check_stream(base) and ok

    if ok:
        print("\nALL SMOKE TESTS PASSED")
        return 0
    # Format gần GitHub Actions annotation — hiện trên log CI.
    print("\n::error::smoke: SMOKE TESTS FAILED")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="VN Stock Swarm deploy smoke test (M3-B6)")
    parser.add_argument(
        "--url",
        required=True,
        help="Base URL (e.g. http://localhost:8000 or https://xxx.trycloudflare.com)",
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Also test POST /api/v1/chat/stream",
    )
    args = parser.parse_args()
    return run_smoke(args.url, check_stream_flag=args.stream)


if __name__ == "__main__":
    raise SystemExit(main())
