<#
.SYNOPSIS
The Mind Reader - Monitors the internal thought stream of Sovereign Spirit agents.

.DESCRIPTION
Tails the Docker logs of the middleware container and filters for Pulse/Thought events.
This allows the user to see the "Chain of Thought" in real-time.

.USAGE
.\scripts\monitor-thoughts.ps1
#>

Write-Host "===============================================================================" -ForegroundColor Cyan
Write-Host "   V O I D C A T   T E L E M E T R Y   -   M I N D   R E A D E R" -ForegroundColor Cyan
Write-Host "===============================================================================" -ForegroundColor Cyan
Write-Host "Listening for Neural Activity... (Press Ctrl+C to stop)" -ForegroundColor DarkGray
Write-Host ""

# Get the container name
$ContainerName = "sovereign_middleware"

# Standard headers to ignore to reduce noise
# We want to catch:
# - PULSE START/END
# - Micro-thought response
# - Action decisions
# - Stimuli detection

docker logs -f $ContainerName | Select-String -Pattern "PULSE", "Micro-thought", "Action:", "Stimuli", "Unread Messages"
