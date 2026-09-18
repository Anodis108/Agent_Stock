#!/usr/bin/env python3
"""Run AI service on port 8001 (Phase 3a).

    python scripts/serve_ai.py
"""

from __future__ import annotations

import argparse

import uvicorn

from src.portfolio_watch.shared.settings import settings


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve Portfolio Watch AI API")
    parser.add_argument("--host", default=settings.ai_api_host)
    parser.add_argument("--port", type=int, default=settings.ai_api_port)
    args = parser.parse_args()
    print(f"AI service: http://{args.host}:{args.port}/  (Ctrl+C to stop)", flush=True)
    uvicorn.run(
        "src.portfolio_watch.ai_main:app",
        host=args.host,
        port=args.port,
        reload=False,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
