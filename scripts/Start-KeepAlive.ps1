<#
.SYNOPSIS
    Sovereign Spirit: Start-KeepAlive
    Prevents Windows from logging out or sleeping during testing.

.DESCRIPTION
    1. Temporarily disables monitor and standby timeouts.
    2. Runs the keep_alive.py script to signal activity.
    3. Restores original power settings on exit.
#>

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonScript = Join-Path $ScriptDir "keep_alive.py"

# Store current power settings
Write-Host "Sovereign Spirit: Capturing current power settings..." -ForegroundColor Cyan
$OriginalMonitorAC = powercfg /query SCHEME_CURRENT SUB_VIDEO VIDEOIDLE | Select-String "Current AC Power Setting Index" | ForEach-Object { $_.ToString().Split(':')[-1].Trim() }
$OriginalStandbyAC = powercfg /query SCHEME_CURRENT SUB_SLEEP STANDBYIDLE | Select-String "Current AC Power Setting Index" | ForEach-Object { $_.ToString().Split(':')[-1].Trim() }

function Restore-PowerSettings {
    Write-Host "`nSovereign Spirit: Restoring original power settings..." -ForegroundColor Yellow
    powercfg /setacvalueindex SCHEME_CURRENT SUB_VIDEO VIDEOIDLE $OriginalMonitorAC
    powercfg /setacvalueindex SCHEME_CURRENT SUB_SLEEP STANDBYIDLE $OriginalStandbyAC
    powercfg /setactive SCHEME_CURRENT
    Write-Host "Sovereign Spirit: Original settings restored." -ForegroundColor Green
}

# Apply Keep-Alive settings
Write-Host "Sovereign Spirit: Disabling timeouts..." -ForegroundColor Cyan
powercfg /setacvalueindex SCHEME_CURRENT SUB_VIDEO VIDEOIDLE 0
powercfg /setacvalueindex SCHEME_CURRENT SUB_SLEEP STANDBYIDLE 0
powercfg /setactive SCHEME_CURRENT

try {
    Write-Host "Sovereign Spirit: Launching Python Keep-Alive..." -ForegroundColor Cyan
    python $PythonScript
}
catch {
    Write-Host "An error occurred: $_" -ForegroundColor Red
}
finally {
    Restore-PowerSettings
}
