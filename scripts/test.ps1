# Lint, tests and build for both halves. Exits non-zero if any step fails.
$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$py = Join-Path $backend ".venv\Scripts\python.exe"
$failed = @()

function Invoke-Check([string]$label, [string]$dir, [scriptblock]$cmd) {
    Write-Host "==> $label" -ForegroundColor Cyan
    Push-Location $dir
    try {
        & $cmd
        if ($LASTEXITCODE -ne 0) { $script:failed += $label }
    } finally { Pop-Location }
}

Invoke-Check "ruff check" $backend { & $py -m ruff check . }
Invoke-Check "ruff format --check" $backend { & $py -m ruff format --check . }
Invoke-Check "pytest" $backend { & $py -m pytest -q }
Invoke-Check "vitest" $frontend { npm test }
Invoke-Check "tsc + vite build" $frontend { npm run build }

if ($failed.Count -gt 0) {
    Write-Host "FAILED: $($failed -join ', ')" -ForegroundColor Red
    exit 1
}
Write-Host "All checks passed." -ForegroundColor Green
