# Reads settings from backend/.env for dev.ps1 / stop.ps1 (dot-source this file).
function Get-DotEnv([string]$Key) {
    $file = Join-Path (Split-Path -Parent $PSScriptRoot) "backend\.env"
    if (-not (Test-Path $file)) { return "" }
    foreach ($line in Get-Content $file) {
        if ($line -match "^\s*$Key\s*=\s*(.*)$") { return $Matches[1].Trim().Trim("'", '"') }
    }
    return ""
}

# Staging (D-28): local port of the SSH tunnel to the server's desktop socket, or $null.
function Get-TunnelPort {
    $vnc = Get-DotEnv "DESKTOP_VNC"
    if ((Get-DotEnv "REMOTE_SSH") -and $vnc -match "^tcp:127\.0\.0\.1:(\d+)$") { return [int]$Matches[1] }
    return $null
}
