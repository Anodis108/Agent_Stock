#!/usr/bin/env bash
# ==============================================================================
# VN Stock Swarm — Script Khởi Chạy Backend & Web UI Cục Bộ (Bash / macOS / Linux)
# Lệnh chuẩn: uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
# ==============================================================================

set -e

# Xác định thư mục gốc của dự án
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

HOST="${1:-127.0.0.1}"
PORT="${2:-8000}"

echo "========================================================"
echo "  VN Stock Swarm & Portfolio Watch — Khởi Chạy Cục Bộ   "
echo "========================================================"
echo "Thư mục dự án: ${PROJECT_ROOT}"

# 1. Kiểm tra file cấu hình môi trường .env
ENV_FILE="${PROJECT_ROOT}/.env"
ENV_EXAMPLE="${PROJECT_ROOT}/.env.example"

if [ ! -f "${ENV_FILE}" ]; then
    if [ -f "${ENV_EXAMPLE}" ]; then
        echo "[INFO] Chưa tìm thấy file .env, tự động tạo từ .env.example..."
        cp "${ENV_EXAMPLE}" "${ENV_FILE}"
        echo "[OK] Đã tạo file .env thành công."
    else
        echo "[WARN] Không tìm thấy .env hoặc .env.example, sẽ sử dụng biến môi trường mặc định."
    fi
fi

# 2. Định vị Python Virtual Environment
PYTHON_BIN=""
VENV_CANDIDATES=(
    "${HOME}/.venv/bin/python"
    "${PROJECT_ROOT}/.venv/bin/python"
    "${PROJECT_ROOT}/venv/bin/python"
)

for candidate in "${VENV_CANDIDATES[@]}"; do
    if [ -f "${candidate}" ] && [ -x "${candidate}" ]; then
        PYTHON_BIN="${candidate}"
        break
    fi
done

if [ -z "${PYTHON_BIN}" ]; then
    if command -v python3 >/dev/null 2>&1; then
        PYTHON_BIN="$(command -v python3)"
    elif command -v python >/dev/null 2>&1; then
        PYTHON_BIN="$(command -v python)"
    else
        echo "[ERROR] Không tìm thấy Python trên hệ thống!"
        echo "Vui lòng cài đặt Python >= 3.10 hoặc khởi tạo virtualenv: python3 -m venv ~/.venv"
        exit 1
    fi
fi

echo "Sử dụng Python: ${PYTHON_BIN}"

# 3. Thiết lập biến môi trường
export PYTHONPATH="${PROJECT_ROOT}/src"
export PYTHONIOENCODING="utf-8"

# 4. Hiển thị thông tin truy cập
echo ""
echo "--------------------------------------------------------"
echo "  Web App UI (Giao diện chính) : http://${HOST}:${PORT}"
echo "  Tài liệu API (Swagger UI)    : http://${HOST}:${PORT}/docs"
echo "  Kiểm tra sức khỏe (Health)   : http://${HOST}:${PORT}/health"
echo "--------------------------------------------------------"
echo ""
echo "[INFO] Đang khởi động máy chủ Uvicorn... (Nhấn Ctrl+C để dừng)"

# 5. Khởi chạy Uvicorn Server
exec "${PYTHON_BIN}" -m uvicorn backend.main:app --host "${HOST}" --port "${PORT}" --reload
