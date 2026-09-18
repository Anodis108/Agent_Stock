#!/usr/bin/env python3
"""Phase 8 — E2E: 1 chat (UI→Backend path = AI /v1/chat) → Langfuse 1 root + spans.

Modes:
  python scripts/phase8_langfuse_e2e.py           # live (needs MONITORING + keys + host)
  python scripts/phase8_langfuse_e2e.py --print-checklist
  python -m pytest tests/test_phase8_langfuse_e2e.py -q
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CHECKLIST = """
Phase 8 — Langfuse E2E checklist (MONITORING_ENABLED=true + valid keys)

Prerequisites:
  .env: MONITORING_ENABLED=true, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST
  pip install langfuse
  Langfuse UI reachable (e.g. http://localhost:3000)
  Terminal 1: python scripts/serve_ai.py          # :8001 (reads .env)
  Terminal 2: python scripts/serve_backend.py     # :8000
  Terminal 3: python scripts/serve_frontend.py    # :5173
  Open http://127.0.0.1:5173/

UI checklist:
  [ ] 1. Chat: "Gia FPT?" -> Timeline steps + final answer; note request_id in Network tab (Backend /chat)
  [ ] 2. Open Langfuse UI -> Traces / Observations
  [ ] 3. Find newest root name=chat (or filter by request_id in metadata)
  [ ] 4. Confirm child spans include: rewrite_question, supervisor, answer_composer
      (+ price_news_fetch when price route)

Automated live probe (no browser):
  python scripts/phase8_langfuse_e2e.py
""".strip()


def _load_env() -> None:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=True)
    cert = os.environ.get("SSL_CERT_FILE")
    if cert and not os.path.isfile(cert):
        os.environ.pop("SSL_CERT_FILE", None)


def _configure_settings() -> bool:
    from src.portfolio_watch.infra.monitoring.tracing import reset_client_for_tests
    from src.portfolio_watch.shared.settings import settings

    pk = (os.environ.get("LANGFUSE_PUBLIC_KEY") or "").strip()
    sk = (os.environ.get("LANGFUSE_SECRET_KEY") or "").strip()
    host = (os.environ.get("LANGFUSE_HOST") or "").strip().rstrip("/")
    enabled = (os.environ.get("MONITORING_ENABLED") or "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    if not enabled or not pk or not sk or not host:
        return False
    settings.monitoring_enabled = True
    settings.langfuse_public_key = pk
    settings.langfuse_secret_key = sk
    settings.langfuse_host = host
    reset_client_for_tests()
    return True


def _run_chat(request_id: str) -> dict:
    from fastapi.testclient import TestClient

    from src.portfolio_watch.ai_main import app
    from src.portfolio_watch.api.deps import AppDeps, set_app_deps
    from src.portfolio_watch.domain.entities import WatchlistItem
    from src.portfolio_watch.domain.ports import PriceQuote
    from tests.fakes import (
        FakeMemoryStore,
        FakeNewsSource,
        FakeNotifier,
        FakePriceHistoryStore,
        FakePriceSource,
        FakeWatchlistStore,
    )

    set_app_deps(
        AppDeps(
            price_source=FakePriceSource(
                PriceQuote("FPT", latest_close=105.0, prev_close=100.0)
            ),
            news_source=FakeNewsSource([[]]),
            history_store=FakePriceHistoryStore([]),
            memory_store=FakeMemoryStore(),
            notifier=FakeNotifier(),
            watchlist_store=FakeWatchlistStore(
                [WatchlistItem(symbol="FPT", threshold_pct=3.0)]
            ),
        )
    )
    try:
        client = TestClient(app)
        resp = client.post(
            "/v1/chat",
            json={"question": "Gia FPT hien tai?", "request_id": request_id},
        )
        data = resp.json()
        data["_http_status"] = resp.status_code
        return data
    finally:
        set_app_deps(None)


def _find_chat_trace(since: datetime, *, attempts: int = 12) -> tuple[object | None, list[str]]:
    from langfuse import Langfuse
    from src.portfolio_watch.shared.settings import settings

    lf = Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_host,
    )
    found = None
    names: list[str] = []
    for _ in range(attempts):
        obs = lf.api.observations.get_many(limit=100)
        roots = [
            o
            for o in obs.data
            if o.name == "chat"
            and o.is_root_observation
            and o.start_time
            and o.start_time >= since
        ]
        if roots:
            found = sorted(roots, key=lambda o: o.start_time)[-1]
            all_obs = lf.api.observations.get_many(limit=150).data
            names = sorted({o.name for o in all_obs if o.trace_id == found.trace_id})
            break
        time.sleep(1)
    return found, names


def run_live() -> int:
    _load_env()
    if not _configure_settings():
        print(
            "SKIP: need MONITORING_ENABLED=true and LANGFUSE_PUBLIC_KEY/"
            "SECRET_KEY/HOST in .env"
        )
        return 2

    from src.portfolio_watch.infra.monitoring.tracing import reset_client_for_tests

    rid = "phase8-e2e-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    since = datetime.now(timezone.utc) - timedelta(seconds=5)
    print("request_id=", rid)
    body = _run_chat(rid)
    print("http_status=", body.get("_http_status"))
    print("has_answer=", bool(body.get("answer")))
    if body.get("_http_status") != 200 or not body.get("answer"):
        print("FAIL: chat did not succeed")
        reset_client_for_tests()
        return 1

    time.sleep(1)
    root, names = _find_chat_trace(since)
    reset_client_for_tests()
    if root is None:
        print("FAIL: no root observation name=chat found on Langfuse")
        return 1

    expected = {"chat", "rewrite_question", "supervisor", "answer_composer"}
    ok = expected <= set(names)
    print("trace_id=", getattr(root, "trace_id", None))
    print("root_id=", getattr(root, "id", None))
    print("span_names=", names)
    print("expected_subset_ok=", ok)
    if not ok:
        print("FAIL: missing spans", sorted(expected - set(names)))
        return 1
    print("PASS: 1 chat -> 1 root chat + agent spans on Langfuse")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--print-checklist",
        action="store_true",
        help="Print UI manual checklist only",
    )
    args = parser.parse_args()
    if args.print_checklist:
        sys.stdout.buffer.write((CHECKLIST + "\n").encode("utf-8", errors="replace"))
        return 0
    return run_live()


if __name__ == "__main__":
    raise SystemExit(main())
