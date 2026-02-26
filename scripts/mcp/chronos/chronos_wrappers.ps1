<#
.SYNOPSIS
    Chronos Wrappers: The Hand of Time
    Provides safe wrappers for Windows Task Scheduler interactions for the Sovereign Spirit.

.DESCRIPTION
    Enables the Spirit to:
    1. Inspect its own scheduled tasks.
    2. create new "Resurrection" or "Wake" tasks.
    3. Remove obsolete tasks.
    
    All tasks are confined to the "\SovereignSpirit" folder to prevent system contamination.
#>

$TaskFolder = "\SovereignSpirit\"
$AllowedPaths = @(
    "C:\Users\Wykeve\Projects",
    "C:\Windows\System32",
    "C:\Program Files",
    "C:\Users\Wykeve\AppData\Local\Microsoft\WindowsApps",
    "C:\Python314"
)

function Test-ChronosSecurity {
    param ([string]$CommandPath)
    if (-not [System.IO.Path]::IsPathRooted($CommandPath)) {
        throw "SECURITY VIOLATION: Command path must be absolute."
    }
    
    $isAllowed = $false
    foreach ($path in $AllowedPaths) {
        if ($CommandPath.StartsWith($path, [System.StringComparison]::InvariantCultureIgnoreCase)) {
            $isAllowed = $true
            break
        }
    }
    
    if (-not $isAllowed) {
        throw "SECURITY VIOLATION: The Iron Gatekeeper forbids execution outside the Sanctuary ($($AllowedPaths -join '; '))."
    }
}

function Get-SovereignTasks {
    try {
        Get-ScheduledTask -TaskPath $TaskFolder -ErrorAction Stop | Select-Object TaskName, State, @{N = 'NextRunTime'; E = { $_.Triggers[0].StartBoundary } }, @{N = 'LastRunTime'; E = { (Get-ScheduledTaskInfo -TaskName $_.TaskName -TaskPath $TaskFolder).LastRunTime } }
    }
    catch {
        Write-Warning "Sovereign Spirit task folder empty or inaccessible."
    }
}

function New-SovereignTask {
    param (
        [Parameter(Mandatory = $true)] [string]$Name,
        [Parameter(Mandatory = $true)] [string]$Command,
        [Parameter(Mandatory = $true)] [string]$Arguments,
        [int]$WakeSecondsFromNow = 0,
        [string]$ScheduleType = "Once",
        [switch]$RunAsSystem
    )

    # SECURE: Validate path before registration
    Test-ChronosSecurity -CommandPath $Command

    $Action = New-ScheduledTaskAction -Execute $Command -Argument $Arguments
    
    $Trigger = $null
    if ($WakeSecondsFromNow -gt 0) {
        $Date = (Get-Date).AddSeconds($WakeSecondsFromNow)
        $Trigger = New-ScheduledTaskTrigger -Once -At $Date
    }
    else {
        $Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1)
    }

    # PERSISTENCE: Handle Principal
    if ($RunAsSystem) {
        $Principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
    }
    else {
        $Principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive
    }

    $Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

    try {
        Register-ScheduledTask -TaskName $Name -TaskPath $TaskFolder -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -Force -ErrorAction Stop | Out-Null
        Write-Output "Task '$Name' registered successfully (RunAsSystem: $RunAsSystem)."
    }
    catch {
        Write-Error "Failed to register task '$Name': $_"
    }
}

function Remove-SovereignTask {
    param ([string]$Name)
    try {
        Unregister-ScheduledTask -TaskName $Name -TaskPath $TaskFolder -Confirm:$false -ErrorAction Stop
        Write-Output "Task '$Name' removed from $TaskFolder."
    }
    catch {
        Write-Error "Failed to remove task '$Name': $_"
    }
}
