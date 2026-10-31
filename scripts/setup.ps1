# One-time setup on Windows: backend venv + deps, .env files, frontend node_modules.
# Nothing is installed globally. Safe to re-run.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$py = Join-Path $backend ".venv\Scripts\python.exe"

function Invoke-Step([string]$label, [scriptblock]$cmd) {
    Write-Host "==> $label" -ForegroundColor Cyan
    & $cmd
    if ($LASTEXITCODE -ne 0) { throw "$label failed (exit $LASTEXITCODE)" }
}

if (-not (Test-Path $py)) {
    Invoke-Step "Create backend\.venv" { python -m venv (Join-Path $backend ".venv") }
}
Invoke-Step "Install backend requirements" {
    & $py -m pip install --disable-pip-version-check -q -r (Join-Path $backend "requirements-dev.txt")
}

foreach ($dir in @($backend, $frontend)) {
    $example = Join-Path $dir ".env.example"
    $target = Join-Path $dir ".env"
    if ((Test-Path $example) -and -not (Test-Path $target)) {
        Copy-Item $example $target
        Write-Host "Created $target"
    }
}

Push-Location $frontend
try { Invoke-Step "npm install" { npm install --no-fund --no-audit } } finally { Pop-Location }

Write-Host "Setup done. Next: scripts\dev.ps1" -ForegroundColor Green
