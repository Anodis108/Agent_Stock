#!/usr/bin/env python3
"""Run Backend API on port 8000 (Phase 3b).

    python scripts/serve_backend.py
"""

from __future__ import annotations

import argparse
import os

import uvicorn
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(".env"), override=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve Portfolio Watch Backend")
    parser.add_argument("--host", default=os.environ.get("API_HOST", "127.0.0.1"))
    parser.add_argument(
        "--port", type=int, default=int(os.environ.get("API_PORT", "8000"))
    )
    args = parser.parse_args()
    print(
        f"Backend: http://{args.host}:{args.port}/  AI_BASE_URL="
        f"{os.environ.get('AI_BASE_URL', 'http://127.0.0.1:8001')}",
        flush=True,
    )
    uvicorn.run("backend.main:app", host=args.host, port=args.port, reload=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
