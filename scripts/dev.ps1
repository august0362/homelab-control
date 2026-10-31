# Opens backend (auto-reload) and frontend (Vite) in two PowerShell windows.
$root = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $root "backend\.venv\Scripts\python.exe"))) {
    Write-Host "Missing backend\.venv. Run scripts\setup.ps1 first." -ForegroundColor Red
    exit 1
}
if (Get-NetTCPConnection -LocalPort 8000, 5173 -State Listen -ErrorAction SilentlyContinue) {
    Write-Host "Already running (port 8000 or 5173 in use). Run stop.bat first." -ForegroundColor Yellow
    exit 1
}

Start-Process powershell -WorkingDirectory (Join-Path $root "backend") `
    -ArgumentList "-NoExit", "-Command", "& .\.venv\Scripts\python.exe -m app --reload"
Start-Process powershell -WorkingDirectory (Join-Path $root "frontend") `
    -ArgumentList "-NoExit", "-Command", "npm run dev"

Write-Host "Backend : http://127.0.0.1:8000/api/health"
Write-Host "Frontend: http://localhost:5173"
