# VoidCat RDC - Real-time MBU Telemetry
$DurationSeconds = 300
$Interval = 2
$OutputFile = "logs/telemetry_mbu.csv"

Write-Host "Monitoring MBU Telemetry..." -ForegroundColor Yellow
"Timestamp,Used_VRAM_MB,MBU_Efficiency_Pct" | Out-File $OutputFile -Encoding ascii

$Elapsed = 0
while ($Elapsed -lt $DurationSeconds) {
    $VramRaw = nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits
    if ($VramRaw -is [array]) { $VramRaw = $VramRaw -join "" }
    $VramUsed = if ($VramRaw -match "(\d+)") { [int]$matches[1] } else { 0 }
    $Efficiency = ($VramUsed / 8192) * 100
    "$((Get-Date).ToString('HH:mm:ss')),$VramUsed,$($Efficiency.ToString('F2'))" | Add-Content $OutputFile
    Start-Sleep -Seconds $Interval
    $Elapsed += $Interval
}
Write-Host "Log session complete." -ForegroundColor Green
Write-Host "Log session complete." -ForegroundColor Green
