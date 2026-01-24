# VoidCat RDC - Master Inference Controller
param (
    [Parameter(Mandatory=$true)]
    [ValidateSet("up", "down", "status", "deploy")]
    $Action,
    [string]$Model = "voidcat-qwen"
)

$ConfigPath = "C:\Users\Wykeve\Projects\The Great Library\20_Projects\01_Active\Sovereign Spirit\config"
$ModelsPath = "C:\Models\lmstudio-community"

switch ($Action) {
    'deploy' {
        Write-Host '⚔️ Manifesting Sovereign Spirits...' -ForegroundColor Magenta
        Write-Host '-> Binding Qwen3-4B-Thinking (4096 ctx)...' -ForegroundColor Cyan
        ollama create voidcat-qwen -f "$ConfigPath\Modelfile.qwen"
        Write-Host '-> Binding GLM-4.6V-Flash (8192 ctx)...' -ForegroundColor Cyan
        ollama create voidcat-glm -f "$ConfigPath\Modelfile.glm"
        Write-Host '-> Pulling Mistral-7B Baseline...' -ForegroundColor Cyan
        ollama pull mistral:7b-instruct-v0.2-q4_K_M
        Write-Host '✅ Deployment Complete.' -ForegroundColor Green
    }
    'up' {
        docker-compose -f "$ConfigPath\docker-compose.yml" -f "$ConfigPath\docker-compose.middleware.yml" up -d
    }
    'down' {
        docker-compose -f "$ConfigPath\docker-compose.yml" -f "$ConfigPath\docker-compose.middleware.yml" down
    }
    'status' {
        ollama list
        docker ps --filter 'name=voidcat'
    }
}
