#!/usr/bin/env python3
"""Phase 7 — xác nhận máy sạch / dong312: README 3 process → 3 luồng chính.

Chạy từ thư mục project:

    python scripts/verify_clean_local.py

Mặc định: tạo venv tạm + pip install -e ., stub AI, Backend, Frontend
(cổng tạm), kiểm health + watchlist + chat + scan + approve/reject.

Dùng env hiện tại (vd. conda dong312) — bỏ qua venv tạm:

    VERIFY_USE_CURRENT=1 python scripts/verify_clean_local.py

In ra CLEAN_VENV_SMOKE_OK khi đủ 3 luồng (chat / giám sát-scan / HITL).
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
USE_CURRENT = os.environ.get("VERIFY_USE_CURRENT", "").lower() in (
    "1",
    "true",
    "yes",
)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def http(
    base: str,
    method: str,
    path: str,
    body: dict | None = None,
    timeout: float = 60,
):
    data = None
    headers: dict[str, str] = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        f"{base}{path}", data=data, headers=headers, method=method
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
        return resp.status, (json.loads(raw) if raw else {})


def wait_health(base: str, *, tries: int = 90) -> dict:
    for _ in range(tries):
        try:
            st, health = http(base, "GET", "/health", timeout=2)
            if st == 200 and health.get("status") == "ok":
                return health
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
            time.sleep(0.4)
    raise RuntimeError(f"unhealthy: {base}/health")


STUB_AI = r"""
from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok", "service": "stub-ai"}

class ChatIn(BaseModel):
    question: str
    user_id: str = "default"

class ScanIn(BaseModel):
    symbol: str
    user_id: str = "default"
    threshold_pct: float | None = None

@app.post("/v1/chat")
def chat(body: ChatIn):
    return {
        "answer": f"FPT đóng cửa 100.0 (stub). Hỏi: {body.question}",
        "symbol": "FPT",
        "steps": [
            {"id": "1", "name": "rewrite_question", "status": "done"},
            {"id": "2", "name": "price_agent", "status": "done"},
            {"id": "3", "name": "answer_composer", "status": "done"},
        ],
    }

@app.post("/v1/scan")
def scan(body: ScanIn):
    sym = (body.symbol or "FPT").upper()
    return {
        "symbol": sym,
        "route": "abnormal",
        "steps": [
            {"id": "1", "name": "price_agent", "status": "done"},
            {"id": "2", "name": "event_classifier", "status": "done"},
        ],
        "pending_events": [
            {"id": f"pend-{sym}", "symbol": sym, "gate": "gate1"}
        ],
        "gate1_action": "pending",
    }
"""


def main() -> int:
    tmpdir = Path(tempfile.mkdtemp(prefix="pw-clean7-"))
    ai_port = _free_port()
    be_port = _free_port()
    fe_port = _free_port()
    be_db = tmpdir / "backend_store.db"
    stub_path = tmpdir / "stub_ai.py"
    stub_path.write_text(STUB_AI, encoding="utf-8")
    print("tmpdir", tmpdir)
    print(f"ports ai={ai_port} backend={be_port} frontend={fe_port}")

    if USE_CURRENT:
        py = sys.executable
        print("using current interpreter", py)
    else:
        venv = tmpdir / ".venv"
        subprocess.check_call([sys.executable, "-m", "venv", str(venv)])
        py = str(
            venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        )
        pip = str(venv / ("Scripts/pip.exe" if os.name == "nt" else "bin/pip"))
        subprocess.check_call([py, "-m", "pip", "install", "-U", "pip"], cwd=str(ROOT))
        subprocess.check_call([pip, "install", "-e", str(ROOT)], cwd=str(ROOT))

    env = os.environ.copy()
    env["OPENAI_API_KEYS"] = env.get("OPENAI_API_KEYS") or "not-needed"
    env["API_HOST"] = "127.0.0.1"
    env["API_PORT"] = str(be_port)
    env["AI_BASE_URL"] = f"http://127.0.0.1:{ai_port}"
    env["BACKEND_SQLITE_PATH"] = str(be_db)
    env["FRONTEND_ORIGIN"] = "*"
    # Tránh seed/conflict từ .env project ghi đè path khi override=False
    env.pop("DOTENV_PATH", None)

    procs: list[subprocess.Popen] = []
    try:
        # 1) Stub AI (= process AI trong README)
        ai = subprocess.Popen(
            [
                py,
                "-m",
                "uvicorn",
                "stub_ai:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(ai_port),
            ],
            cwd=str(tmpdir),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        procs.append(ai)
        wait_health(f"http://127.0.0.1:{ai_port}")
        print("AI health ok (stub)")

        # 2) Backend
        be = subprocess.Popen(
            [
                py,
                "-m",
                "uvicorn",
                "backend.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(be_port),
            ],
            cwd=str(ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        procs.append(be)
        be_base = f"http://127.0.0.1:{be_port}"
        wait_health(be_base)
        print("Backend health ok")

        # 3) Frontend static
        fe = subprocess.Popen(
            [
                py,
                "-m",
                "http.server",
                str(fe_port),
                "--bind",
                "127.0.0.1",
                "--directory",
                str(ROOT / "frontend"),
            ],
            cwd=str(ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        procs.append(fe)
        for _ in range(40):
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{fe_port}/", timeout=2
                ) as resp:
                    html = resp.read().decode("utf-8", errors="replace")
                if 'id="chat"' in html and 'id="watchlist"' in html:
                    print("Frontend UI ok")
                    break
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
                time.sleep(0.3)
        else:
            raise RuntimeError("frontend not serving index.html")

        # Luồng 1 — watchlist (seed / CRUD)
        st, item = http(
            be_base, "POST", "/watchlist", {"symbol": "FPT", "threshold_pct": 3.0}
        )
        assert st == 200 and item.get("symbol") == "FPT"
        st, wl = http(be_base, "GET", "/watchlist")
        assert st == 200 and any(i["symbol"] == "FPT" for i in wl.get("items") or [])
        print("watchlist ok")

        # Luồng 2 — chat + timeline steps
        st, chat = http(
            be_base, "POST", "/chat", {"question": "Giá FPT hôm nay?"}
        )
        assert st == 200
        assert "FPT" in (chat.get("answer") or "")
        steps = chat.get("steps") or []
        assert len(steps) >= 2
        assert all(s.get("status") and s.get("name") for s in steps)
        assert chat.get("run_id")
        print("chat + steps ok")

        # Luồng 3 — scan + HITL duyệt
        st, scan = http(be_base, "POST", "/scan", {"symbol": "FPT"})
        assert st == 200 and scan.get("symbol") == "FPT"
        assert scan.get("steps")
        st, approvals = http(be_base, "GET", "/approvals")
        assert st == 200 and (approvals.get("count") or 0) >= 1
        aid = approvals["items"][0]["id"]
        st, ap = http(be_base, "POST", f"/approvals/{aid}/approve", {})
        assert st == 200 and ap.get("ok") is True
        st, after = http(be_base, "GET", "/approvals")
        assert after.get("count", 0) == 0
        print("scan + hitl approve ok")

        print("CLEAN_VENV_SMOKE_OK")
        return 0
    finally:
        for p in reversed(procs):
            p.terminate()
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()


if __name__ == "__main__":
    raise SystemExit(main())
