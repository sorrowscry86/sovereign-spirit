# VoidCat RDC - Inference Baseline Test Suite
param (
    [string[]]$Models = @("voidcat-qwen", "voidcat-glm", "mistral:7b-instruct-v0.2-q4_K_M")
)

$Prompt = "Explain the mechanics of a mana-based economy in three short paragraphs, then provide a JSON schema for a 'ManaTransfer' transaction."
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
$LogFile = Join-Path $PSScriptRoot "..\logs\baseline_results.json"
# Ensure the log file is initialized as an empty array or at least exists
"[" | Out-File $LogFile -Encoding utf8

Write-Host "🧪 Starting Baseline Inference Tests..." -ForegroundColor Cyan
foreach ($Model in $Models) {
    Write-Host "-> Testing Model: $Model" -ForegroundColor Yellow
    $StartTime = Get-Date

    # Execute with a 60-second limit to prevent ghost hangs
    $Job = Start-Job -ScriptBlock { param($m, $p) ollama run $m $p } -ArgumentList $Model, $Prompt
    if ($Job | Wait-Job -Timeout 60) {
        $Response = Receive-Job $Job
    }
    else {
        $Response = "[ERROR] Timeout reached (60s)."
        Stop-Job $Job
    }
    Remove-Job $Job

    $EndTime = Get-Date
    $Duration = ($EndTime - $StartTime).TotalSeconds
    $Result = [PSCustomObject]@{
        Model = $Model; Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss";
        DurationSeconds = $Duration; ResponseLength = if ($Response) { $Response.ToString().Length } else { 0 };
        Status = if ($Response -match "ERROR") { "Failed" } else { "Success" }
    }
    $Json = $Result | ConvertTo-Json -Compress
    if ($Model -ne $Models[-1]) { $Json += "," }
    $Json | Add-Content $LogFile
}
"]" | Add-Content $LogFile
Write-Host "✅ Testing complete." -ForegroundColor Green
