# OmniMarket Intelligence Terminal - one-command launcher (Windows PowerShell)
# Usage:  powershell -ExecutionPolicy Bypass -File .\start.ps1
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

Write-Host "`n  OMNIMARKET  Intelligence Terminal`n" -ForegroundColor Cyan

if (-not (Test-Path "$root\.venv\Scripts\python.exe")) {
    Write-Host "> Creating Python virtual environment..."
    python -m venv .venv
}
Write-Host "> Installing / verifying Python dependencies..."
& "$root\.venv\Scripts\python.exe" -m pip install -q -r requirements.txt

if (-not (Test-Path "$root\.env")) { Copy-Item "$root\.env.example" "$root\.env"; Write-Host "> Created .env from .env.example" }

if (-not (Test-Path "$root\frontend\node_modules")) {
    Write-Host "> Installing frontend dependencies (npm)..."
    Push-Location "$root\frontend"; npm install --no-fund --no-audit; Pop-Location
}

Write-Host "> Starting API on http://localhost:8000 (docs: /docs)"
$api = Start-Process -FilePath "$root\.venv\Scripts\python.exe" -ArgumentList "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000" -WorkingDirectory $root -PassThru -WindowStyle Minimized

Write-Host "> Starting UI on http://localhost:5173"
$ui = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "npx vite --host 127.0.0.1 --port 5173" -WorkingDirectory "$root\frontend" -PassThru -WindowStyle Minimized

Start-Sleep -Seconds 4
Start-Process "http://localhost:5173"
Write-Host "`n  Running. Press Ctrl+C here to stop both servers.`n" -ForegroundColor Green
try { while ($true) { Start-Sleep -Seconds 2; if ($api.HasExited) { Write-Host "API exited (see logs\)"; break } } }
finally {
    foreach ($p in @($api, $ui)) { if ($p -and -not $p.HasExited) { taskkill /PID $p.Id /T /F | Out-Null } }
}
