<#
.SYNOPSIS
    Starts the TalentGraph local development environment (FastAPI Backend + Next.js Frontend).

.DESCRIPTION
    Ensures .env and web/.env.local exist, starts the FastAPI backend (in-memory or docker backed),
    waits for health readiness, and launches the Next.js dev server. Terminating the script
    (Ctrl+C) cleanly stops all child services.

.PARAMETER BackendOnly
    Start only the FastAPI backend on port 8000.

.PARAMETER FrontendOnly
    Start only the Next.js frontend on port 3000.

.PARAMETER BindHost
    Bind host for the backend (default: 127.0.0.1).

.PARAMETER BackendPort
    Port for the FastAPI backend (default: 8000).

.PARAMETER FrontendPort
    Port for the Next.js frontend (default: 3000).
#>

param(
    [switch]$BackendOnly,
    [switch]$FrontendOnly,
    [string]$BindHost = "127.0.0.1",
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 3000
)

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

# 1. Ensure root .env exists
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Write-Host "Notice: .env not found. Initializing from .env.example with defaults..." -ForegroundColor Yellow
        Copy-Item ".env.example" ".env"
    } else {
        Write-Error "Neither .env nor .env.example found in $RepoRoot"
        exit 1
    }
}

# 2. Ensure web/.env.local exists
if (-not (Test-Path "web\.env.local")) {
    $webEnvContent = @"
BACKEND_URL=http://${BindHost}:${BackendPort}
NEXT_PUBLIC_API_URL=http://${BindHost}:${BackendPort}
"@
    Set-Content -Path "web\.env.local" -Value $webEnvContent -Encoding utf8
    Write-Host "Notice: Created web/.env.local pointing to backend at http://${BindHost}:${BackendPort}" -ForegroundColor DarkGray
}

if ($BackendOnly) {
    Write-Host "Starting TalentGraph Backend on http://${BindHost}:${BackendPort}..." -ForegroundColor Cyan
    uv run uvicorn talentgraph.api.main:app --host $BindHost --port $BackendPort --reload
    exit $LASTEXITCODE
}

if ($FrontendOnly) {
    Write-Host "Starting TalentGraph Frontend on http://localhost:${FrontendPort}..." -ForegroundColor Cyan
    Set-Location web
    npm run dev
    exit $LASTEXITCODE
}

Write-Host "==========================================================" -ForegroundColor Green
Write-Host " Starting TalentGraph (Backend :$BackendPort + Frontend :$FrontendPort)" -ForegroundColor Green
Write-Host " Press Ctrl+C to terminate both services." -ForegroundColor DarkGray
Write-Host "==========================================================" -ForegroundColor Green

$backendProcess = Start-Process -FilePath "uv" -ArgumentList "run", "uvicorn", "talentgraph.api.main:app", "--host", $BindHost, "--port", "$BackendPort" -PassThru -NoNewWindow

Write-Host "Waiting for backend to be ready..." -ForegroundColor Cyan
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Milliseconds 500
    try {
        $res = Invoke-RestMethod -Uri "http://${BindHost}:${BackendPort}/health" -TimeoutSec 1 -ErrorAction Stop
        if ($res.status -eq "ok") {
            $ready = $true
            break
        }
    } catch {}
}

if ($ready) {
    Write-Host "[OK] Backend is live at http://${BindHost}:${BackendPort}" -ForegroundColor Green
} else {
    Write-Host "[!] Backend taking longer to initialize, starting frontend now..." -ForegroundColor Yellow
}

try {
    Set-Location web
    npm run dev
} finally {
    Write-Host ""
    Write-Host "Stopping backend process..." -ForegroundColor Yellow
    if ($backendProcess -and -not $backendProcess.HasExited) {
        try {
            Get-CimInstance Win32_Process | Where-Object { $_.ParentProcessId -eq $backendProcess.Id } | ForEach-Object {
                Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
            }
        } catch {}
        Stop-Process -Id $backendProcess.Id -Force -ErrorAction SilentlyContinue
    }
    Write-Host "Services stopped cleanly." -ForegroundColor Green
}
