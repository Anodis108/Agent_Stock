<#
.SYNOPSIS
    VN Stock Swarm — Release & Deployment Management Script (PowerShell)
.DESCRIPTION
    Quản lý vòng đời release cho môi trường triển khai cục bộ (Local / Docker Compose):
    - up: Khởi chạy dịch vụ với docker compose và kiểm tra sức khỏe
    - smoke: Chạy bộ kiểm thử tự động nhanh (src/deploy/smoke.py)
    - rollback: Hoàn nguyên bản phát hành trước đó (LKG / Prompt Rollback)
    - status: Kiểm tra trạng thái các container và endpoints (health check)
    Triển khai thuần cục bộ trên máy trạm Windows.
#>

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet("up", "smoke", "rollback", "status")]
    [string]$Action = "status",

    [string]$Url = "http://127.0.0.1:8000",
    [switch]$Stream
)

$ErrorActionPreference = "Stop"

# Xác định thư mục gốc của dự án
$DeployDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $DeployDir
Set-Location $ProjectRoot

# File lưu trạng thái Last-Known-Good (LKG) cho rollback
$LkgFile = Join-Path $DeployDir ".release_lkg"

# Định vị Python Environment
function Get-PythonPath {
    $candidates = @(
        "$HOME\.venv\Scripts\python.exe",
        "C:\Users\ADMIN\miniconda3\envs\dong312\python.exe",
        (Join-Path $ProjectRoot ".venv\Scripts\python.exe"),
        "python.exe"
    )
    foreach ($cand in $candidates) {
        if (Test-Path $cand) { return $cand }
    }
    return "python"
}

$Python = Get-PythonPath

function Invoke-Up {
    Write-Host "[RELEASE] Executing: up" -ForegroundColor Cyan
    
    # 1. Đảm bảo file .env tồn tại
    $envFile = Join-Path $ProjectRoot ".env"
    $envExample = Join-Path $ProjectRoot ".env.example"
    if (-not (Test-Path $envFile) -and (Test-Path $envExample)) {
        Copy-Item $envExample $envFile
        Write-Host "[INFO] Đã tạo .env từ .env.example" -ForegroundColor Yellow
    }

    # 2. Lưu trạng thái trước khi up để phục vụ rollback (LKG)
    $currentSha = git rev-parse HEAD 2>$null
    if ($currentSha) {
        Set-Content -Path $LkgFile -Value $currentSha -Encoding utf8
    }

    # 3. Khởi chạy các service với docker compose
    Write-Host "[INFO] Khởi chạy containers: postgres, qdrant, backend, ai_backend..." -ForegroundColor Cyan
    docker compose up -d postgres qdrant backend ai_backend

    # 4. Hiển thị trạng thái sau khi up
    Write-Host "[OK] Dịch vụ đã khởi chạy. Kiểm tra trạng thái..." -ForegroundColor Green
    Invoke-Status
}

function Invoke-Smoke {
    Write-Host "[RELEASE] Executing: smoke test -> $Url" -ForegroundColor Cyan
    $smokeScript = Join-Path $DeployDir "smoke.py"
    $argsList = @($smokeScript, "--url", $Url)
    if ($Stream) {
        $argsList += "--stream"
    }

    $env:PYTHONPATH = (Join-Path $ProjectRoot "src")
    & $Python @argsList
    $smokeExit = $LASTEXITCODE
    if ($smokeExit -eq 0) {
        Write-Host "[OK] Smoke test hoàn thành thành công!" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] Smoke test thất bại (exit code $smokeExit)!" -ForegroundColor Red
        exit $smokeExit
    }
}

function Invoke-Rollback {
    Write-Host "[RELEASE] Executing: rollback" -ForegroundColor Yellow

    # 1. Rollback prompt version nếu có script prompt_rollback.py
    $promptRollbackScript = Join-Path $ProjectRoot "scripts\prompt_rollback.py"
    if (Test-Path $promptRollbackScript) {
        Write-Host "[INFO] Rollback prompt alias production.txt..." -ForegroundColor Cyan
        $env:PYTHONPATH = (Join-Path $ProjectRoot "src")
        & $Python $promptRollbackScript
    }

    # 2. Rollback docker container về trạng thái ổn định
    Write-Host "[INFO] Tái khởi động lại container về trạng thái ổn định..." -ForegroundColor Cyan
    docker compose up -d --force-recreate postgres qdrant backend ai_backend

    # 3. Chạy lại smoke test để xác nhận sau rollback
    Write-Host "[INFO] Chạy smoke test xác nhận sau khi rollback..." -ForegroundColor Cyan
    Invoke-Smoke
}

function Invoke-Status {
    Write-Host "[RELEASE] Executing: status" -ForegroundColor Cyan
    Write-Host "--- Docker Compose Containers ---" -ForegroundColor Gray
    docker compose ps

    Write-Host "`n--- Endpoint Health Checks ---" -ForegroundColor Gray
    $endpoints = @(
        @{ Name = "Web Backend"; Url = "http://127.0.0.1:8000/health" },
        @{ Name = "AI Backend "; Url = "http://127.0.0.1:8001/health" }
    )

    foreach ($ep in $endpoints) {
        try {
            $resp = Invoke-RestMethod -Uri $ep.Url -Method Get -TimeoutSec 5 -ErrorAction Stop
            Write-Host "[$($ep.Name)] $($ep.Url) -> OK" -ForegroundColor Green
        } catch {
            Write-Host "[$($ep.Name)] $($ep.Url) -> NOT REACHABLE ($($_.Exception.Message))" -ForegroundColor Red
        }
    }
}

switch ($Action.ToLower()) {
    "up"       { Invoke-Up }
    "smoke"    { Invoke-Smoke }
    "rollback" { Invoke-Rollback }
    "status"   { Invoke-Status }
    default    { Invoke-Status }
}
