# Headless LM Studio (`llmster`) Deployment Guide

**Version:** 1.0
**Target:** Linux Servers (Ubuntu/Debian), CI/CD Pipelines, Raspberry Pi 5+
**Purpose:** Deploy Sovereign Spirit in a headless environment without a GUI, optimizing resources for the model.

## 1. Installation

### Linux / Mac
Run the official installer. This installs both the CLI (`lms`) and the daemon (`llmster`).

```bash
curl -fsSL https://lmstudio.ai/install.sh | bash
```

### Windows (Server Core / Headless)
```powershell
irm https://lmstudio.ai/install.ps1 | iex
```

## 2. Service Management

The core service is `llmster`. You must start the daemon before using the CLI or API.

### Start Daemon
```bash
lms daemon up
```
*Tip: Use `nohup lms daemon up &` or a systemd service to keep it running.*

### Stop Daemon
```bash
lms daemon down
```

## 3. Model Management

You can manage models entirely via CLI.

### Search for Models
```bash
lms search qwen2.5
```

### Download a Model
```bash
# Downloads to ~/.cache/lm-studio/models
lms get qwen2.5-7b-instruct
```

### Load a Model (Headless Server)
Start the local server and load a specific model.
```bash
lms server start --model qwen2.5-7b-instruct --port 1234
```

## 4. Integration with Sovereign Spirit

### Environment Configuration
Ensure your `.env` or `docker-compose.yml` points to the headless instance.

```env
# Point to the headless server
LM_STUDIO_HOST=http://localhost:1234
# Optional: Enforce specific model IDs for Bifrost Routing
LM_STUDIO_REASONING_MODEL=qwen2.5-7b-instruct
LM_STUDIO_DIRECT_MODEL=mistral-7b-instruct
```

### SDK Usage
The `src/core/llm_client.py` uses the `lmstudio` SDK, which automatically connects to the standard port.

```python
# The client will auto-detect the model loaded by 'lms server start'
# unless specific model IDs are requested via complexity routing.
client = LLMClient(active_provider="lm_studio")
```

## 5. CI/CD Workflow (GitHub Actions)

Example workflow step to test Sovereign Spirit logic against a real model:

```yaml
steps:
  - name: Install LM Studio
    run: curl -fsSL https://lmstudio.ai/install.sh | bash
  
  - name: Start Daemon
    run: lms daemon up &
  
  - name: Load Model
    run: lms server start --model qwen2.5-0.5b-instruct --port 1234 &
    
  - name: Run Tests
    run: pytest tests/
```
*Note: Use smaller models (0.5b) for CI to save time/bandwidth.*
