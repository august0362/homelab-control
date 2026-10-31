# Sets the owner login password (D-23). Asks twice, hidden; stores only a scrypt hash
# in backend\.env. Restart the backend afterwards; existing sessions are signed out.
$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"
$py = Join-Path $backend ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Host "Missing backend\.venv. Run scripts\setup.ps1 first." -ForegroundColor Red
    exit 1
}
Push-Location $backend
try { & $py -m app set-password } finally { Pop-Location }
exit $LASTEXITCODE
