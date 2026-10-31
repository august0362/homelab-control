# Opens backend (auto-reload) and frontend (Vite) in two PowerShell windows, plus the
# SSH tunnel to the server's remote desktop when backend/.env sets it up (staging, D-28).
$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot "env.ps1")
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

$port = Get-TunnelPort
if ($port -and -not (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)) {
    $alias = Get-DotEnv "REMOTE_SSH"
    $runtime = & ssh -o BatchMode=yes -o ConnectTimeout=5 $alias 'echo $XDG_RUNTIME_DIR' 2>$null
    if ($LASTEXITCODE -eq 0 -and $runtime) {
        Start-Process ssh -WindowStyle Hidden -ArgumentList "-N", "-o", "BatchMode=yes", "-o", "ExitOnForwardFailure=yes",
            "-o", "ServerAliveInterval=15", "-L", "127.0.0.1:${port}:$($runtime.Trim())/hlc-vnc.sock", $alias
        Write-Host "Desktop : tunnel to the server on 127.0.0.1:$port"
    } else {
        Write-Host "Desktop : server not reachable over SSH; Remote Desktop will show it as stopped." -ForegroundColor Yellow
    }
}

Write-Host "Backend : http://127.0.0.1:8000/api/health"
Write-Host "Frontend: http://localhost:5173"
