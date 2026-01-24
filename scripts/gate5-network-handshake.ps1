# VoidCat RDC - Gate 5 Network Handshake
# Authority: Beatrice (Guardian)
# Method: Native PowerShell (Minimal Try/Catch)

$ErrorActionPreference = "Continue"

$ProjectDir = "C:\Users\Wykeve\Projects\The Great Library\20_Projects\01_Active\Sovereign Spirit"
$ConfigDir = Join-Path $ProjectDir "config"
$ScaffoldingDir = "c:\Users\Wykeve\.gemini\antigravity\playground\scaffolding"

Write-Host "--- [GATE 5 NETWORK HANDSHAKE] ---" -ForegroundColor Cyan

# 1. Validate Configuration Files
Write-Host "[1/5] Validating Compose Syntax..." -ForegroundColor Gray
docker-compose -f "$ConfigDir\docker-compose.yml" -f "$ConfigDir\docker-compose.middleware.yml" config > $null
if ($LASTEXITCODE -eq 0) { Write-Host "  -> Core Stack Config: VALID" -ForegroundColor Green }

docker-compose -f "$ScaffoldingDir\docker-compose.yml" -f "$ScaffoldingDir\docker-compose.middleware.yml" config > $null
if ($LASTEXITCODE -eq 0) { Write-Host "  -> Inference Scaffolding Config: VALID" -ForegroundColor Green }

# 2. Manifest the Stack
Write-Host "[2/5] Awakening Infrastructure..." -ForegroundColor Gray
docker-compose -f "$ConfigDir\docker-compose.yml" -f "$ConfigDir\docker-compose.middleware.yml" up -d
docker-compose -f "$ScaffoldingDir\docker-compose.yml" -f "$ScaffoldingDir\docker-compose.middleware.yml" up -d

# 3. Verify Security Boundaries (Shielding)
Write-Host "[3/5] Testing Security Boundaries (Host -> Shielded)..." -ForegroundColor Gray
$ShieldedPorts = @(5432, 6379, 8001, 8002, 7474)
foreach ($P in $ShieldedPorts) {
    $Connect = Test-NetConnection -ComputerName localhost -Port $P -WarningAction SilentlyContinue
    if ($Connect.TcpTestSucceeded) {
        Write-Host "  [!] WARNING: Port $P is EXPOSED to host!" -ForegroundColor Yellow
    }
    else {
        Write-Host "  -> Port $P : SHIELDED [OK]" -ForegroundColor Green
    }
}

# 4. Verify Middleware Proxy (Handshake)
Write-Host "[4/5] Testing Middleware Handshake..." -ForegroundColor Gray
$Endpoints = @(
    @{ Name = "Sovereign Middleware (Memory)"; Url = "http://localhost:8080/health"; Expected = "online" },
    @{ Name = "Inference Gateway (Reranker/Vision)"; Url = "http://localhost:8005/health"; Expected = "gateway_ok" }
)

foreach ($EP in $Endpoints) {
    $Res = try { Invoke-RestMethod -Uri $EP.Url -ErrorAction Stop } catch { $null }
    if ($null -ne $Res -and $Res.status -eq $EP.Expected) {
        Write-Host "  -> $($EP.Name) : OPERATIONAL [OK]" -ForegroundColor Green
    }
    else {
        $Status = if ($null -ne $Res) { $Res.status } else { "UNREACHABLE" }
        Write-Host "  -> $($EP.Name) : FAILED ($Status)" -ForegroundColor Red
    }
}

# 5. Verify Monitoring Gateway
Write-Host "[5/5] Testing Monitoring Gateway..." -ForegroundColor Gray
$Mon = try { Invoke-RestMethod -Uri "http://localhost:9090/health" -ErrorAction Stop } catch { $null }
if ($null -ne $Mon) {
    Write-Host "  -> Monitor Service (Port 9090): ACTIVE [OK]" -ForegroundColor Green
}
else {
    Write-Host "  -> Monitor Service (Port 9090): OFFLINE" -ForegroundColor Red
}

Write-Host "`n--- [HANDSHAKE COMPLETE] ---" -ForegroundColor Cyan
Write-Host "GATE 5 STATUS: ASSESSMENT COMPLETE" -ForegroundColor Yellow
