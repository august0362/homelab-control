# Production build: frontend/dist is served by the backend on the same origin.
$root = Split-Path -Parent $PSScriptRoot
Push-Location (Join-Path $root "frontend")
try { npm run build } finally { Pop-Location }
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Built frontend\dist." -ForegroundColor Green
Write-Host "run: cd backend; .\.venv\Scripts\python -m app -> http://127.0.0.1:8000"
