"""Script tự động khởi chạy và quản lý đường hầm Ngrok phục vụ Demo Public.

Cách sử dụng:
    python scripts/start_ngrok_demo.py [--port 8000] [--token YOUR_AUTHTOKEN]
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
import requests

try:
    from pyngrok import conf, ngrok
except ImportError:
    print("Vui lòng cài đặt pyngrok: pip install pyngrok")
    sys.exit(1)

# Đảm bảo in UTF-8 an toàn trên Windows console
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def load_env_file() -> None:
    """Tự động nạp các biến môi trường từ file .env nếu có."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        try:
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = val
        except Exception:
            pass



def check_backend_running(port: int = 8000) -> bool:
    try:
        res = requests.get(f"http://127.0.0.1:{port}/health", timeout=3)
        return res.status_code == 200
    except Exception:
        return False


def main() -> None:
    load_env_file()
    parser = argparse.ArgumentParser(description="Portfolio Watch — Ngrok Demo Runner")
    parser.add_argument("--port", type=int, default=8000, help="Cổng backend local (mặc định: 8000)")
    parser.add_argument("--token", type=str, default="", help="Ngrok Authtoken (nếu chưa lưu trong config)")
    parser.add_argument("--check-only", action="store_true", help="Chỉ kiểm tra khả năng sẵn sàng demo")
    args = parser.parse_args()

    print("=" * 60)
    print("🚀 PORTFOLIO WATCH — NGROK PUBLIC DEMO SETUP")
    print("=" * 60)

    # 1. Kiểm tra Backend
    print(f"[*] Kiểm tra trạng thái Backend tại http://127.0.0.1:{args.port}/health ...")
    if not check_backend_running(args.port):
        print(f"[!] CẢNH BÁO: Backend chưa khởi động trên cổng {args.port}!")
        print(f"[*] Hãy chạy lệnh sau trên một cửa sổ terminal khác trước khi demo:")
        print(f"    $env:PYTHONPATH='src'; python -m uvicorn backend.main:app --port {args.port} --host 127.0.0.1")
        if not args.check_only:
            sys.exit(1)
    else:
        print(f"[✓] Backend đang hoạt động ổn định trên cổng {args.port}.")

    if args.check_only:
        print("[✓] Kiểm tra sẵn sàng hoàn tất. Môi trường sẵn sàng để expose demo.")
        return

    # 2. Cấu hình Authtoken nếu có
    token = args.token or os.environ.get("NGROK_AUTHTOKEN")
    if token:
        ngrok.set_auth_token(token)
        print("[*] Đã cấu hình Ngrok Authtoken.")
    else:
        print("[!] Lưu ý: Chưa phát hiện NGROK_AUTHTOKEN. Ngrok có thể yêu cầu đăng ký tài khoản miễn phí.")
        print("[*] Lấy token tại: https://dashboard.ngrok.com/get-started/your-authtoken")

    # 3. Mở Tunnel
    print(f"[*] Đang tạo đường hầm HTTP tới cổng {args.port}...")
    try:
        tunnel = ngrok.connect(args.port, "http")
        public_url = tunnel.public_url
        if public_url.startswith("http://"):
            public_url = public_url.replace("http://", "https://")

        print("\n" + "=" * 60)
        print(f"✨ PUBLIC DEMO URL: {public_url}")
        print(f"📖 API Docs:       {public_url}/docs")
        print(f"🩺 Health Check:   {public_url}/health")
        print("=" * 60 + "\n")

        # Kiểm tra thử qua Public URL
        try:
            r = requests.get(f"{public_url}/health", timeout=10)
            if r.status_code == 200:
                print(f"[✓] Public Health Check thành công qua URL: {public_url}/health")
        except Exception as e:
            print(f"[!] Không thể kiểm tra public url ngay lập tức: {e}")

        print("\n[+] Đang duy trì tunnel. Nhấn Ctrl+C để dừng demo.")
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[*] Đang đóng đường hầm Ngrok...")
        ngrok.kill()
        print("[✓] Đã dừng demo thành công.")
    except Exception as exc:
        print(f"[X] Lỗi khởi tạo Ngrok: {exc}")
        print("[*] Bạn cũng có thể cài đặt native ngrok CLI và chạy:")
        print(f"    ngrok http {args.port}")
        sys.exit(1)


if __name__ == "__main__":
    main()
