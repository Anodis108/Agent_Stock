<#
.SYNOPSIS
    VN Stock Swarm — Cloudflare Tunnel Publishing Script (PowerShell)
.DESCRIPTION
    Khoi chay Cloudflare Tunnel (cloudflared) de mo mot URL HTTPS cong khai ra Internet
    tro truc tiep vao Nginx cong 80 cuc bo (127.0.0.1:80), khong can mo port modem,
    khong can mua ten mien, trien khai thuan cuc bo tren may tram Windows.
#>

[CmdletBinding()]
param(
    [string]$TargetUrl = "http://127.0.0.1:80",
    [switch]$CheckOnly
)

$ErrorActionPreference = "Stop"

$DeployDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $DeployDir

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " VN Stock Swarm - Cloudflare Tunnel Publisher" -ForegroundColor Cyan
Write-Host " Target: $TargetUrl (Nginx Port 80)" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Tim kiem binary cloudflared
function Find-Cloudflared {
    $cmd = Get-Command "cloudflared" -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }

    $candidates = @(
        "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\Cloudflare.cloudflared*\cloudflared.exe",
        "$env:ProgramFiles\cloudflared\cloudflared.exe",
        "$HOME\bin\cloudflared.exe",
        (Join-Path $ProjectRoot "cloudflared.exe"),
        (Join-Path $DeployDir "cloudflared.exe")
    )

    foreach ($pattern in $candidates) {
        $matches = Get-ChildItem -Path $pattern -ErrorAction SilentlyContinue
        if ($matches) {
            return $matches[0].FullName
        }
    }

    return $null
}

$CloudflaredPath = Find-Cloudflared

if (-not $CloudflaredPath) {
    Write-Host ""
    Write-Host "[CANH BAO] Khong tim thay 'cloudflared' tren he thong!" -ForegroundColor Yellow
    Write-Host "De mo URL HTTPS ra internet qua Cloudflare Tunnel, vui long cai dat cloudflared:" -ForegroundColor Gray
    Write-Host "  Cach 1 (WinGet): winget install --id Cloudflare.cloudflared" -ForegroundColor White
    Write-Host "  Cach 2 (Thu cong): Tai cloudflared-windows-amd64.exe tu https://github.com/cloudflare/cloudflared/releases" -ForegroundColor White
    Write-Host "                    doi ten thanh cloudflared.exe va dat vao thu muc du an hoac PATH." -ForegroundColor White
    if ($CheckOnly) {
        exit 0
    }
    exit 1
}

Write-Host "[OK] Da tim thay cloudflared: $CloudflaredPath" -ForegroundColor Green

# 2. Kiem tra Nginx tren cong 80 co san sang
try {
    $resp = Invoke-WebRequest -Uri $TargetUrl -UseBasicParsing -TimeoutSec 3 -ErrorAction SilentlyContinue
    if ($resp.StatusCode -eq 200) {
        Write-Host "[OK] Cong Nginx ($TargetUrl) dang phan hoi tot (HTTP 200)." -ForegroundColor Green
    } else {
        Write-Host "[INFO] Cong Nginx ($TargetUrl) phan hoi voi ma HTTP: $($resp.StatusCode)." -ForegroundColor Yellow
    }
} catch {
    Write-Host "[CANH BAO] Chua ket noi duoc toi $TargetUrl. Hay chac chan Nginx hoac Docker Compose da chay:" -ForegroundColor Yellow
    Write-Host "  Chay: powershell -ExecutionPolicy Bypass -File src/deploy/release.ps1 up" -ForegroundColor Gray
}

if ($CheckOnly) {
    Write-Host ""
    Write-Host "[DONE] Kiem tra hoan tat (Che do CheckOnly)." -ForegroundColor Green
    exit 0
}

# 3. Khoi chay Cloudflare Tunnel
Write-Host ""
Write-Host "[INFO] Dang khoi chay Cloudflare Tunnel toi $TargetUrl..." -ForegroundColor Cyan
Write-Host "[HUONG DAN] Sau vai giay, cloudflared se in ra mot duong dan dang:" -ForegroundColor Gray
Write-Host "  https://<random-subdomain>.trycloudflare.com" -ForegroundColor White
Write-Host "Hay sao chep URL https do de gui cho nguoi dung hoac kiem tra GET /health." -ForegroundColor Gray
Write-Host ""

& $CloudflaredPath tunnel --url $TargetUrl
