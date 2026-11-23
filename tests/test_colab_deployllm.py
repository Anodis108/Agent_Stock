"""Gọi model đang chạy trên Colab (vLLM + ngrok) từ máy local.

  export COLAB_NGROK_URL="https://xxxx.ngrok-free.app"
  python test_colab_deployllm.py            # chat thường
  python test_colab_deployllm.py --stream   # stream token (OpenAI-compatible)
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import requests

DEFAULT_BASE = "https://d245-136-85-27-195.ngrok-free.app"


def resolve_base() -> str:
    base = os.environ.get("COLAB_NGROK_URL", DEFAULT_BASE).rstrip("/")
    if base.endswith("/v1/chat/completions"):
        base = base[: -len("/v1/chat/completions")]
    return base


def chat_once(api_url: str, model: str, headers: dict) -> None:
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {
                "role": "user",
                "content": "Hãy viết một bài thơ 4 câu nói về lập trình máy tính.",
            },
        ],
        "temperature": 0.7,
        "top_p": 0.9,
        "max_tokens": 256,
        "stream": False,
    }
    print(f"Đang gửi request tới: {api_url} ...")
    response = requests.post(api_url, headers=headers, json=data, timeout=120)
    if response.status_code == 200:
        result = response.json()
        print("\n--- Phản hồi từ Model ---")
        print(result["choices"][0]["message"]["content"])
    else:
        print(f"Lỗi: {response.status_code}")
        print(response.text)
        sys.exit(1)


def chat_stream(api_url: str, model: str, headers: dict) -> None:
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {
                "role": "user",
                "content": "Hãy viết một bài thơ 4 câu nói về lập trình máy tính.",
            },
        ],
        "temperature": 0.7,
        "top_p": 0.9,
        "max_tokens": 256,
        "stream": True,
    }
    print(f"Streaming từ: {api_url}\n---")
    with requests.post(
        api_url, headers=headers, json=data, stream=True, timeout=120
    ) as resp:
        if resp.status_code != 200:
            print(f"Lỗi: {resp.status_code}")
            print(resp.text)
            sys.exit(1)
        for raw in resp.iter_lines(decode_unicode=True):
            if not raw:
                continue
            if raw.startswith("data: "):
                raw = raw[6:]
            if raw.strip() == "[DONE]":
                print("\n--- [DONE] ---")
                break
            chunk = json.loads(raw)
            delta = chunk["choices"][0].get("delta") or {}
            token = delta.get("content") or ""
            if token:
                print(token, end="", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Gọi /v1/chat/completions với stream=true (chuẩn OpenAI/vLLM)",
    )
    parser.add_argument(
        "--model",
        default="Qwen/Qwen2.5-3B-Instruct",
        help="Tên model phải khớp model vLLM trên Colab",
    )
    args = parser.parse_args()

    base = resolve_base()
    api_url = f"{base}/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "ngrok-skip-browser-warning": "1",
    }

    try:
        chat_stream(api_url, args.model, headers)
        chat_once(api_url, args.model, headers)
    except Exception as e:
        print(f"Không thể kết nối tới server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
