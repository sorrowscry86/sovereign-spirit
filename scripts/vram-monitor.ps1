# ============================================================================
# VOIDCAT RDC: VRAM MONITORING SCRIPT
# ============================================================================
# Purpose: Real-time GPU telemetry for VRAM calibration testing
# Usage: .\vram-monitor.ps1 [-Duration 300] [-Interval 5] [-OutputFile "telemetry.csv"]
# ============================================================================

param(
    [int]$Duration = 300,        # Total monitoring duration in seconds (default: 5 min)
    [int]$Interval = 5,          # Sampling interval in seconds
    [string]$OutputFile = "",    # Optional CSV output file
    [switch]$Continuous          # Run continuously until Ctrl+C
)

$ErrorActionPreference = "Stop"

# Header
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  VOIDCAT SOVEREIGN - VRAM MONITOR v1.0" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Check for nvidia-smi
$nvidiaSmi = Get-Command "nvidia-smi" -ErrorAction SilentlyContinue
if (-not $nvidiaSmi) {
    Write-Host "[ERROR] nvidia-smi not found. Ensure NVIDIA drivers are installed." -ForegroundColor Red
    exit 1
}

# Initialize CSV if output requested
if ($OutputFile) {
    "Timestamp,GPU_Util_Percent,VRAM_Used_MB,VRAM_Total_MB,VRAM_Free_MB,Temperature_C,Power_W" | Out-File $OutputFile -Encoding UTF8
    Write-Host "[INFO] Logging to: $OutputFile" -ForegroundColor Green
}

# Thresholds (8GB RTX 4070)
$VRAM_TOTAL = 8192  # MB
$VRAM_WARNING = 7000  # MB - Yellow zone
$VRAM_CRITICAL = 7500  # MB - Red zone (OOM imminent)

Write-Host "[INFO] Monitoring RTX 4070 (8GB VRAM)" -ForegroundColor Yellow
Write-Host "[INFO] WARNING threshold: ${VRAM_WARNING}MB | CRITICAL threshold: ${VRAM_CRITICAL}MB" -ForegroundColor Yellow
Write-Host "[INFO] Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""
Write-Host "Timestamp            | GPU% | VRAM Used | VRAM Free | Temp | Power | Status" -ForegroundColor White
Write-Host "---------------------+------+-----------+-----------+------+-------+--------" -ForegroundColor Gray

$startTime = Get-Date
$samples = @()

function Get-GpuMetrics {
    $output = & nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total,memory.free,temperature.gpu,power.draw --format=csv,noheader,nounits
    $values = $output.Trim() -split ","
    
    return @{
        GpuUtil = [int]$values[0].Trim()
        VramUsed = [int]$values[1].Trim()
        VramTotal = [int]$values[2].Trim()
        VramFree = [int]$values[3].Trim()
        Temperature = [int]$values[4].Trim()
        Power = [float]$values[5].Trim()
    }
}

try {
    while ($true) {
        $elapsed = ((Get-Date) - $startTime).TotalSeconds
        
        if (-not $Continuous -and $elapsed -ge $Duration) {
            break
        }
        
        $metrics = Get-GpuMetrics
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        
        # Determine status color
        $status = "OK"
        $statusColor = "Green"
        if ($metrics.VramUsed -ge $VRAM_CRITICAL) {
            $status = "CRITICAL"
            $statusColor = "Red"
        } elseif ($metrics.VramUsed -ge $VRAM_WARNING) {
            $status = "WARNING"
            $statusColor = "Yellow"
        }
        
        # Format output
        $line = "{0} | {1,4}% | {2,6}MB | {3,6}MB | {4,3}C | {5,5}W | {6}" -f `
            $timestamp, `
            $metrics.GpuUtil, `
            $metrics.VramUsed, `
            $metrics.VramFree, `
            $metrics.Temperature, `
            $metrics.Power, `
            $status
        
        Write-Host $line -ForegroundColor $statusColor
        
        # Log to CSV if requested
        if ($OutputFile) {
            "$timestamp,$($metrics.GpuUtil),$($metrics.VramUsed),$($metrics.VramTotal),$($metrics.VramFree),$($metrics.Temperature),$($metrics.Power)" | Out-File $OutputFile -Append -Encoding UTF8
        }
        
        # Store sample for summary
        $samples += $metrics
        
        Start-Sleep -Seconds $Interval
    }
} finally {
    # Summary Statistics
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Cyan
    Write-Host "  MONITORING COMPLETE - SUMMARY" -ForegroundColor Cyan
    Write-Host "============================================" -ForegroundColor Cyan
    
    if ($samples.Count -gt 0) {
        $avgVram = [math]::Round(($samples | Measure-Object -Property VramUsed -Average).Average, 0)
        $maxVram = ($samples | Measure-Object -Property VramUsed -Maximum).Maximum
        $minVram = ($samples | Measure-Object -Property VramUsed -Minimum).Minimum
        $avgGpu = [math]::Round(($samples | Measure-Object -Property GpuUtil -Average).Average, 0)
        
        Write-Host "Samples Collected: $($samples.Count)" -ForegroundColor White
        Write-Host "VRAM Usage (MB):   Min=$minVram | Avg=$avgVram | Max=$maxVram" -ForegroundColor White
        Write-Host "GPU Utilization:   Avg=${avgGpu}%" -ForegroundColor White
        Write-Host "Headroom at Max:   $($VRAM_TOTAL - $maxVram)MB" -ForegroundColor $(if ($maxVram -ge $VRAM_CRITICAL) { "Red" } elseif ($maxVram -ge $VRAM_WARNING) { "Yellow" } else { "Green" })
        
        # Recommendation
        Write-Host ""
        if ($maxVram -ge $VRAM_CRITICAL) {
            Write-Host "[RECOMMENDATION] CRITICAL: Layer offloading REQUIRED. Set num_gpu=20-25 in Ollama." -ForegroundColor Red
        } elseif ($maxVram -ge $VRAM_WARNING) {
            Write-Host "[RECOMMENDATION] WARNING: Consider reducing context window to 4096 tokens." -ForegroundColor Yellow
        } else {
            Write-Host "[RECOMMENDATION] STABLE: Full GPU inference viable. Proceed with deployment." -ForegroundColor Green
        }
    }
}
