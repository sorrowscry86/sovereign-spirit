
# Sovereign Spirit Startup Script
# ===============================
# Loads VoidKeys and starts the Docker stack.

Write-Host "🔮 Initializing Sovereign Spirit..." -ForegroundColor Cyan

# 1. Load VoidKeys
try {
    Import-Module "$PSScriptRoot\..\..\..\40_Systems\Ongoing\VoidKey\src\VoidKeyModule.psm1" -Force -ErrorAction Stop
    Load-VoidKeys
}
catch {
    Write-Warning "VoidKey Module not found or failed to load. Using existing environment."
    Write-Error $_
}

# 2. Start Docker Stack
Write-Host "🐳 Launching Containers..." -ForegroundColor Cyan
docker-compose -f "$PSScriptRoot\..\docker-compose.yml" up -d

Write-Host "✅ Sovereign Spirit Active." -ForegroundColor Green
