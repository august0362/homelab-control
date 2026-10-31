# Stops the dev servers from dev.ps1 (ports 8000 and 5173) and closes their windows.
$ports = 8000, 5173
$listeners = Get-NetTCPConnection -LocalPort $ports -State Listen -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique
if (-not $listeners) {
    Write-Host "Nothing is listening on ports $($ports -join ', ')."
    exit 0
}

foreach ($listener in $listeners) {
    # Walk up python/node/cmd parents; stop at the window dev.ps1 opened so it closes too.
    # Any other shell (e.g. your own terminal) is left alone.
    $target = $listener
    $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$listener"
    for ($i = 0; $proc -and $i -lt 10; $i++) {
        if ($proc.Name -in "python.exe", "node.exe", "cmd.exe") {
            $target = $proc.ProcessId
        } elseif ($proc.Name -eq "powershell.exe" -and $proc.CommandLine -match "-NoExit" -and
                  $proc.CommandLine -match "python.exe -m app|npm run dev") {
            $target = $proc.ProcessId
            break
        } else {
            break
        }
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$($proc.ParentProcessId)"
    }
    taskkill /PID $target /T /F 2>&1 | Out-Null
    Write-Host "Stopped PID $target (port listener $listener)."
}
