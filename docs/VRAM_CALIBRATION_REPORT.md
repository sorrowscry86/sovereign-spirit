# VOIDCAT RDC: VRAM CALIBRATION REPORT

**Document Type:** Technical Validation Report  
**Phase:** Week 1, Day 3-4  
**Status:** PENDING EXECUTION  
**Hardware:** RTX 4070 (8GB VRAM) / 16GB System RAM

---

## 1. OBJECTIVE

Validate that the Ollama inference engine can operate alongside the Dockerized Sovereign Stack without triggering Out-Of-Memory (OOM) crashes on consumer hardware.

---

## 2. TEST PROTOCOL

### 2.1 Pre-Test Checklist

- [ ] Docker stack deployed (`docker-compose up -d`)
- [ ] All containers healthy (`docker ps`)
- [ ] Ollama service running
- [ ] Base model pulled: `ollama pull mistral:7b-instruct-v0.2-q4_K_M`
- [ ] Custom model created: `ollama create voidcat-sovereign -f config/ollama-modelfile`
- [ ] Monitoring script ready: `scripts/vram-monitor.ps1`

### 2.2 Test Scenarios

#### Scenario A: Baseline Loading (Idle State)
```powershell
# Terminal 1: Start monitoring
.\scripts\vram-monitor.ps1 -Duration 120 -Interval 5 -OutputFile "baseline.csv"

# Terminal 2: Load model (will auto-unload after timeout)
ollama run voidcat-sovereign "Hello, confirm you are operational."
```

**Expected Result:** VRAM usage stabilizes at ~5.6GB

#### Scenario B: Heavy Desktop Simulation
```powershell
# Actions during monitoring:
# 1. Open 20 browser tabs (various sites)
# 2. Play YouTube video (1080p)
# 3. Open Discord/Slack
# 4. Run inference: ollama run voidcat-sovereign "Write a 500 word essay on memory."
```

**Expected Result:** VRAM peaks below 7.5GB (CRITICAL threshold)

#### Scenario C: Extended Context Stress
```powershell
# Long conversation to fill context window
# Paste a large document (~3000 tokens) and ask for analysis
```

**Expected Result:** Identify if context expansion causes OOM

---

## 3. DECISION MATRIX

| Peak VRAM | Headroom | Status | Action Required |
|:----------|:---------|:-------|:----------------|
| < 7000 MB | > 1 GB | ✅ OPTIMAL | Proceed with full GPU inference |
| 7000-7500 MB | 500MB-1GB | ⚠️ WARNING | Reduce context to 2048 or close browser |
| > 7500 MB | < 500 MB | 🔴 CRITICAL | Enable layer offloading (num_gpu=25) |
| OOM Crash | 0 | ❌ FAILURE | Major reconfiguration required |

---

## 4. LAYER OFFLOADING CONFIGURATION (If Required)

If Scenario B results in CRITICAL or FAILURE status:

```bash
# Edit the modelfile
PARAMETER num_gpu 25  # Offload 7 layers to CPU

# Or for severe constraints:
PARAMETER num_gpu 20  # Offload 12 layers to CPU
PARAMETER num_ctx 2048  # Halve context window
```

**Performance Impact:**
- Full GPU (32 layers): ~50 tokens/sec
- Partial Offload (25 layers): ~25-30 tokens/sec
- Heavy Offload (20 layers): ~15-20 tokens/sec

This latency is acceptable for background agents (Heartbeat) but may feel sluggish for direct chat.

---

## 5. TEST RESULTS

### 5.1 Baseline Loading (Scenario A)

| Metric | Value |
|:-------|:------|
| VRAM at Idle (before load) | _____ MB |
| VRAM after Model Load | _____ MB |
| VRAM during Inference | _____ MB |
| Time to First Token | _____ ms |
| Tokens per Second | _____ t/s |

**Status:** [ ] PASS / [ ] FAIL

### 5.2 Heavy Desktop Simulation (Scenario B)

| Metric | Value |
|:-------|:------|
| Peak VRAM (Max) | _____ MB |
| Average VRAM | _____ MB |
| Minimum Free | _____ MB |
| OOM Events | _____ |
| System Swap Used | _____ MB |

**Status:** [ ] PASS / [ ] FAIL

### 5.3 Extended Context Stress (Scenario C)

| Metric | Value |
|:-------|:------|
| Context Tokens Used | _____ |
| VRAM at Peak | _____ MB |
| Response Quality | _____ |
| Latency Impact | _____ |

**Status:** [ ] PASS / [ ] FAIL

---

## 6. FINAL CONFIGURATION

Based on test results, the following configuration is LOCKED for production:

```
MODEL: voidcat-sovereign
BASE: mistral:7b-instruct-v0.2-q4_K_M
NUM_GPU: _____ (layers on GPU)
NUM_CTX: _____ (context window)
NUM_BATCH: 512
TEMPERATURE: 0.7
```

**Configuration File:** `config/ollama-modelfile`

---

## 7. SIGN-OFF

| Role | Agent | Status | Date |
|:-----|:------|:-------|:-----|
| Test Execution | Wykeve / Ryuzu | PENDING | |
| Configuration Approval | Beatrice | PENDING | |
| Documentation | Claude Opus 4.5 | ✅ COMPLETE | 2026-01-18 |

---

**Next Phase:** Upon successful VRAM calibration, proceed to Week 1 Day 5 — Nervous System (Filesystem Watchers)
