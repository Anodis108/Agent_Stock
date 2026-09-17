#!/usr/bin/env python3
"""Xác nhận Phase 6: virtualenv mới + làm theo README → 3 luồng chính.

Chạy từ thư mục llm-backend-ref:

    python scripts/verify_clean_local.py

Tạo venv tạm, `pip install -e .`, khởi động uvicorn cổng tạm, kiểm
health / UI / watchlist / scan / chat / approve+reject. Không sửa source.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PORT = int(os.environ.get("CLEAN_VERIFY_PORT", "8765"))
BASE = f"http://127.0.0.1:{PORT}"


def http(method: str, path: str, body: dict | None = None, timeout: float = 120):
    data = None
    headers: dict[str, str] = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        f"{BASE}{path}", data=data, headers=headers, method=method
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
        return resp.status, (json.loads(raw) if raw else {})


def main() -> int:
    tmpdir = Path(tempfile.mkdtemp(prefix="pw-clean-"))
    venv = tmpdir / ".venv"
    db = tmpdir / "portfolio_watch.db"
    print("tmpdir", tmpdir)

    subprocess.check_call([sys.executable, "-m", "venv", str(venv)])
    py = str(
        venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    )
    pip = str(venv / ("Scripts/pip.exe" if os.name == "nt" else "bin/pip"))

    subprocess.check_call([py, "-m", "pip", "install", "-U", "pip"], cwd=str(ROOT))
    subprocess.check_call([pip, "install", "-e", str(ROOT)], cwd=str(ROOT))

    env = os.environ.copy()
    env["SQLITE_PATH"] = str(db)
    env["API_PORT"] = str(PORT)
    env["API_HOST"] = "127.0.0.1"
    env["OPENAI_API_KEYS"] = "not-needed"
    # Tránh load_dotenv nhầm .env project ghi đè path (settings: override=False)
    env.pop("DOTENV_PATH", None)

    subprocess.check_call(
        [
            py,
            "-c",
            "from src.portfolio_watch.shared.settings import settings; "
            "from src.portfolio_watch.infra.storage.sqlite_db import connect; "
            "connect(settings.sqlite_path); "
            "print('SQLite OK:', settings.sqlite_path)",
        ],
        cwd=str(ROOT),
        env=env,
    )

    proc = subprocess.Popen(
        [
            py,
            "-m",
            "uvicorn",
            "src.portfolio_watch.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(PORT),
        ],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    try:
        for _ in range(90):
            try:
                st, health = http("GET", "/health", timeout=2)
                if st == 200 and health.get("status") == "ok":
                    print("health ok", health)
                    break
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                time.sleep(0.5)
        else:
            out = (
                proc.stdout.read().decode("utf-8", errors="replace")
                if proc.stdout
                else ""
            )
            raise RuntimeError("server unhealthy\n" + out[:3000])

        with urllib.request.urlopen(f"{BASE}/", timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        assert 'id="chat"' in html
        assert 'id="watchlist"' in html
        assert 'id="approvals"' in html
        print("UI ok")

        st, item = http("POST", "/watchlist", {"symbol": "FPT", "threshold_pct": 3.0})
        assert st == 200 and item["symbol"] == "FPT"
        print("watchlist ok")

        st, scan = http("POST", "/scan", {"symbol": "FPT"})
        assert st == 200 and scan["symbol"] == "FPT" and "price" in scan
        print("scan ok", scan.get("route"), scan["price"].get("error"))

        st, chat = http("POST", "/chat", {"question": "Giá FPT hiện tại?"})
        assert st == 200
        assert chat.get("hitl_used") is False
        assert chat.get("pending_approvals_created", 0) == 0
        assert chat.get("answer")
        print("chat ok")

        st, approvals = http("GET", "/approvals")
        assert st == 200
        gate1 = [i for i in (approvals.get("items") or []) if i.get("gate") == "gate1"]
        if not gate1:
            subprocess.check_call(
                [
                    py,
                    "-c",
                    """
from src.portfolio_watch.infra.storage import SqliteMemoryStore
from src.portfolio_watch.domain.entities import FinalAlert, Severity, SeverityLevel, AlertStatus
import os
mem = SqliteMemoryStore(os.environ['SQLITE_PATH'])
alert = FinalAlert(
    id='clean-a1', symbol='FPT', title='Canh bao FPT', body='change_pct=5.00%',
    severity=Severity(level=SeverityLevel.MEDIUM, confidence=0.4, reasoning='map mo', evidence=['change_pct=5.00%']),
    status=AlertStatus.PENDING_APPROVAL,
)
mem.append_alert_event('default', {
    'kind':'pending_approval','gate':'gate1','alert_id':'clean-a1','symbol':'FPT',
    'status':'pending_approval','alert': alert.model_dump(mode='json'),
})
print('seeded')
""",
                ],
                cwd=str(ROOT),
                env=env,
            )
            st, approvals = http("GET", "/approvals")
            gate1 = [
                i for i in (approvals.get("items") or []) if i.get("gate") == "gate1"
            ]
        assert gate1, "no gate1 pending"
        aid = gate1[0]["approval_id"]
        st, ap = http("POST", f"/approvals/{aid}/approve", {})
        assert st == 200 and ap.get("ok") is True
        assert ap["alert"]["status"] == "sent"
        print("hitl approve ok")

        subprocess.check_call(
            [
                py,
                "-c",
                """
from src.portfolio_watch.infra.storage import SqliteMemoryStore
from src.portfolio_watch.domain.entities import FinalAlert, Severity, SeverityLevel, AlertStatus
import os
mem = SqliteMemoryStore(os.environ['SQLITE_PATH'])
alert = FinalAlert(
    id='clean-a2', symbol='FPT', title='Canh bao FPT', body='change_pct=5.00%',
    severity=Severity(level=SeverityLevel.MEDIUM, confidence=0.4, reasoning='map mo', evidence=['change_pct=5.00%']),
    status=AlertStatus.PENDING_APPROVAL,
)
mem.append_alert_event('default', {
    'kind':'pending_approval','gate':'gate1','alert_id':'clean-a2','symbol':'FPT',
    'status':'pending_approval','alert': alert.model_dump(mode='json'),
})
""",
            ],
            cwd=str(ROOT),
            env=env,
        )
        st, rj = http("POST", "/approvals/clean-a2/reject", {"reason": "tin nhiễu"})
        assert st == 200 and rj.get("ok") is True
        assert rj["alert"]["reject_reason"] == "tin nhiễu"
        print("hitl reject ok")
        print("CLEAN_VENV_SMOKE_OK")
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
