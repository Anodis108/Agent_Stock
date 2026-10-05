# ==============================================================================
# VN Stock Swarm — Script Khởi Chạy Backend & Web UI Cục Bộ (PowerShell)
# Lệnh chuẩn: uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
# ==============================================================================

[CmdletBinding()]
param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8000,
    [switch]$NoReload
)

$ErrorActionPreference = "Stop"

# Xác định thư mục gốc của dự án
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  VN Stock Swarm & Portfolio Watch — Khởi Chạy Cục Bộ   " -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "Thư mục dự án: $ProjectRoot" -ForegroundColor Gray

# 1. Kiểm tra file cấu hình môi trường .env
$EnvFile = Join-Path $ProjectRoot ".env"
$EnvExample = Join-Path $ProjectRoot ".env.example"

if (-not (Test-Path $EnvFile)) {
    if (Test-Path $EnvExample) {
        Write-Host "[INFO] Chưa tìm thấy file .env, tự động tạo từ .env.example..." -ForegroundColor Yellow
        Copy-Item $EnvExample $EnvFile
        Write-Host "[OK] Đã tạo file .env thành công." -ForegroundColor Green
    } else {
        Write-Host "[WARN] Không tìm thấy .env hoặc .env.example, sẽ sử dụng biến môi trường mặc định." -ForegroundColor Yellow
    }
}

# 2. Định vị Python Environment
$PythonExe = ""
$VenvCandidates = @(
    "$HOME\.venv\Scripts\python.exe",
    (Join-Path $ProjectRoot ".venv\Scripts\python.exe"),
    (Join-Path $ProjectRoot "venv\Scripts\python.exe")
)

foreach ($candidate in $VenvCandidates) {
    if (Test-Path $candidate) {
        $PythonExe = $candidate
        break
    }
}

if (-not $PythonExe) {
    $SysPython = Get-Command "python" -ErrorAction SilentlyContinue
    if ($SysPython) {
        $PythonExe = $SysPython.Source
    } else {
        Write-Host "[ERROR] Không tìm thấy Python trên hệ thống!" -ForegroundColor Red
        Write-Host "Vui lòng cài đặt Python >= 3.10 hoặc khởi tạo virtualenv: python -m venv `$HOME\.venv" -ForegroundColor Red
        exit 1
    }
}

Write-Host "Sử dụng Python: $PythonExe" -ForegroundColor Gray

# 3. Thiết lập biến môi trường
$env:PYTHONPATH = (Join-Path $ProjectRoot "src")
$env:PYTHONIOENCODING = "utf-8"

# 4. Hiển thị thông tin truy cập
Write-Host "`n--------------------------------------------------------" -ForegroundColor DarkGray
Write-Host "  Web App UI (Giao diện chính) : http://${HostAddress}:${Port}" -ForegroundColor Green
Write-Host "  Tài liệu API (Swagger UI)    : http://${HostAddress}:${Port}/docs" -ForegroundColor Green
Write-Host "  Kiểm tra sức khỏe (Health)   : http://${HostAddress}:${Port}/health" -ForegroundColor Green
Write-Host "--------------------------------------------------------`n" -ForegroundColor DarkGray
Write-Host "[INFO] Đang khởi động máy chủ Uvicorn... (Nhấn Ctrl+C để dừng)" -ForegroundColor Cyan

$ReloadFlag = if ($NoReload) { @() } else { @("--reload") }

# 5. Khởi chạy Uvicorn Server
& $PythonExe -m uvicorn backend.main:app --host $HostAddress --port $Port @ReloadFlag
