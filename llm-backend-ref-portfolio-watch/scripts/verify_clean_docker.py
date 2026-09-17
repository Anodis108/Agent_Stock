#!/usr/bin/env python3
"""Xác nhận Phase 7: máy sạch + Docker Compose → 3 luồng chính.

Chạy từ thư mục llm-backend-ref (cần Docker daemon đang chạy):

    python scripts/verify_clean_docker.py

`docker compose up --build -d`, đợi health, kiểm UI / watchlist / scan /
chat / approve+reject (cùng API mà browser UI gọi). Dừng bằng
`compose down` (giữ volume) trừ khi VERIFY_DOCKER_DOWN_V=1.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import uuid
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PORT = int(os.environ.get("APP_HOST_PORT", os.environ.get("VERIFY_DOCKER_PORT", "8000")))
BASE = f"http://127.0.0.1:{PORT}"
COMPOSE = ["docker", "compose"]


def http(method: str, path: str, body: dict | None = None, timeout: float = 180):
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


def compose(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        [*COMPOSE, *args],
        cwd=str(ROOT),
        check=check,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )


def docker_exec_seed(alert_id: str) -> None:
    code = f"""
from src.portfolio_watch.infra.storage import SqliteMemoryStore
from src.portfolio_watch.domain.entities import FinalAlert, Severity, SeverityLevel, AlertStatus
import os
mem = SqliteMemoryStore(os.environ['SQLITE_PATH'])
alert = FinalAlert(
    id={alert_id!r}, symbol='FPT', title='Canh bao FPT', body='change_pct=5.00%',
    severity=Severity(level=SeverityLevel.MEDIUM, confidence=0.4, reasoning='map mo', evidence=['change_pct=5.00%']),
    status=AlertStatus.PENDING_APPROVAL,
)
mem.append_alert_event('default', {{
    'kind':'pending_approval','gate':'gate1','alert_id':{alert_id!r},'symbol':'FPT',
    'status':'pending_approval','alert': alert.model_dump(mode='json'),
}})
print('seeded', {alert_id!r})
"""
    r = compose("exec", "-T", "app", "python", "-c", code, check=False)
    if r.returncode != 0:
        raise RuntimeError(
            "seed failed\n" + (r.stderr or "") + "\n" + (r.stdout or "")
        )
    print((r.stdout or "").strip())


def main() -> int:
    env_path = ROOT / ".env"
    if not env_path.is_file():
        example = ROOT / ".env.example"
        env_path.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
        print("created .env from .env.example")

    print("compose up --build …")
    up = compose("up", "--build", "-d", check=False)
    if up.returncode != 0:
        print(up.stdout)
        print(up.stderr)
        raise RuntimeError("docker compose up --build failed")

    try:
        for _ in range(120):
            try:
                st, health = http("GET", "/health", timeout=3)
                if st == 200 and health.get("status") == "ok":
                    print("health ok", health)
                    break
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
                time.sleep(1)
        else:
            logs = compose("logs", "app", check=False)
            raise RuntimeError(
                "container unhealthy\n" + (logs.stdout or "")[-4000:]
            )

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
        print("scan ok", scan.get("route"), (scan.get("price") or {}).get("error"))

        st, chat = http("POST", "/chat", {"question": "Giá FPT hiện tại?"})
        assert st == 200
        assert chat.get("hitl_used") is False
        assert chat.get("pending_approvals_created", 0) == 0
        assert chat.get("answer")
        print("chat ok")

        # ID mới mỗi lần — volume SQLite có thể còn resolution cũ
        approve_id = f"docker-a-{uuid.uuid4().hex[:8]}"
        reject_id = f"docker-r-{uuid.uuid4().hex[:8]}"

        docker_exec_seed(approve_id)
        st, approvals = http("GET", "/approvals")
        assert st == 200
        gate1 = [
            i
            for i in (approvals.get("items") or [])
            if i.get("gate") == "gate1" and i.get("approval_id") == approve_id
        ]
        assert gate1, f"no gate1 pending for {approve_id}: {approvals}"
        st, ap = http("POST", f"/approvals/{approve_id}/approve", {})
        assert st == 200 and ap.get("ok") is True
        assert ap["alert"]["status"] == "sent"
        print("hitl approve ok")

        docker_exec_seed(reject_id)
        st, rj = http(
            "POST", f"/approvals/{reject_id}/reject", {"reason": "tin nhiễu"}
        )
        assert st == 200 and rj.get("ok") is True
        assert rj["alert"]["reject_reason"] == "tin nhiễu"
        print("hitl reject ok")
        print("CLEAN_DOCKER_SMOKE_OK")
        return 0
    finally:
        if os.environ.get("VERIFY_DOCKER_DOWN_V") == "1":
            compose("down", "-v", check=False)
            print("compose down -v")
        else:
            compose("down", check=False)
            print("compose down (volume kept)")


if __name__ == "__main__":
    raise SystemExit(main())
