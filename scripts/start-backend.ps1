<#
.SYNOPSIS
    Start the SupportPilot AI backend reliably on port 8000.

.DESCRIPTION
    Kills any process that currently owns the port, waits until the port is
    genuinely free, starts Uvicorn detached, then waits for /api/health to
    answer. A previous incident was caused by a stale Uvicorn instance still
    holding the port: the new instance could not bind, exited silently, and the
    server looked healthy until the stale process exited.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts/start-backend.ps1
#>
param(
    [int]$Port = 8000,
    [string]$BindHost = "127.0.0.1",
    [switch]$Foreground
)

$ErrorActionPreference = "Stop"
$backendDir = Join-Path $PSScriptRoot "..\backend"
$venvPython = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $venvPython)) {
    throw "Virtual environment not found at $venvPython. Create it and run: pip install -r backend\requirements.txt"
}
if (-not (Test-Path -LiteralPath (Join-Path $backendDir "app\main.py"))) {
    throw "Backend application not found in $backendDir"
}

function Get-PortOwner {
    param([int]$TargetPort)
    $conn = Get-NetTCPConnection -LocalPort $TargetPort -State Listen -ErrorAction SilentlyContinue
    if ($conn) { return $conn[0].OwningProcess }
    return $null
}

# 1. Stop whatever currently owns the port (this is what was missed before).
$owner = Get-PortOwner -TargetPort $Port
if ($owner) {
    Write-Host "Port $Port is held by PID $owner - stopping it."
    Stop-Process -Id $owner -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
}

# 2. Wait for the port to be released, otherwise the new server cannot bind.
$deadline = (Get-Date).AddSeconds(15)
while ((Get-Date) -lt $deadline) {
    if (-not (Get-PortOwner -TargetPort $Port)) { break }
    Start-Sleep -Milliseconds 500
}
if (Get-PortOwner -TargetPort $Port) {
    throw "Port $Port is still occupied after waiting. Aborting instead of starting a server that cannot bind."
}
Write-Host "Port $Port is free."

# 3. Start the server.
Push-Location $backendDir
try {
    if ($Foreground) {
        Write-Host "Starting Uvicorn in the foreground (Ctrl+C to stop)..."
        & $venvPython -m uvicorn app.main:app --host $BindHost --port $Port
        exit $LASTEXITCODE
    }

    $stdout = Join-Path $backendDir "uvicorn.log"
    $stderr = Join-Path $backendDir "uvicorn.err.log"
    $process = Start-Process -FilePath $venvPython `
        -ArgumentList "-m", "uvicorn", "app.main:app", "--host", $BindHost, "--port", $Port `
        -WorkingDirectory $backendDir `
        -RedirectStandardOutput $stdout -RedirectStandardError $stderr `
        -WindowStyle Hidden -PassThru
    Write-Host "Started Uvicorn (PID $($process.Id)). Logs: $stdout"
}
finally {
    Pop-Location
}

# 4. Wait until the API actually answers, and confirm the listener is alive.
$health = $null
$deadline = (Get-Date).AddSeconds(45)
while ((Get-Date) -lt $deadline) {
    try {
        $health = Invoke-RestMethod "http://${BindHost}:$Port/api/health" -TimeoutSec 3
        break
    } catch {
        Start-Sleep -Milliseconds 700
    }
}

if (-not $health) {
    Write-Host "Backend did not become healthy in time. Last log lines:" -ForegroundColor Red
    Get-Content (Join-Path $backendDir "uvicorn.err.log") -Tail 20 -ErrorAction SilentlyContinue
    exit 1
}

$owner = Get-PortOwner -TargetPort $Port
Write-Host "Backend healthy at http://${BindHost}:$Port (listener PID $owner, status $($health.status), version $($health.version))." -ForegroundColor Green

