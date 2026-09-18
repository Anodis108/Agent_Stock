#!/usr/bin/env python3
"""Serve frontend/ trên 5173 (Phase 2 — độc lập Backend/AI).

    python scripts/serve_frontend.py
    # mở http://127.0.0.1:5173/
"""

from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FE = ROOT / "frontend"
DEFAULT_PORT = 5173


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve Portfolio Watch frontend")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()
    if not FE.is_dir():
        print(f"missing {FE}")
        return 1
    handler = partial(SimpleHTTPRequestHandler, directory=str(FE))
    httpd = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"Frontend: http://{args.host}:{args.port}/  (Ctrl+C to stop)", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
