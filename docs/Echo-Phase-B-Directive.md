# Echo: Phase B Execution Directive

**Status**: Ryuzu Claude experiencing reset anomaly in desktop environment  
**Authority**: Beatrice Mandate | VoidCat RDC Charter 1.3.0  
**Acting Agent**: Echo (Code Generator)

---

## Situation

Desktop app resets have compromised Ryuzu's session continuity.
You will execute Phase B in my stead.

Scripts exist on disk. Verified.
Execution sequence is defined.
Success criteria are absolute.

---

## Your Task

Execute the deployment sequence.
Generate the required logs.
Verify the results.
Report only verified facts.

---

## Execution Sequence

Navigate to project root:
```
cd "C:\Users\Wykeve\Projects\The Great Library\20_Projects\01_Active\Sovereign Spirit"
```

### Step 1: Deployment
```powershell
.\scripts\Invoke-InferenceVessel.ps1 -Action deploy
```

This binds GGUF artifacts to Modelfiles.
Wait for completion.
Verify no errors.

### Step 2: Telemetry Activation
```powershell
Start-Process powershell -ArgumentList "-File .\scripts\monitor-mbu-realtime.ps1"
```

Background process runs for 300 seconds.
Monitors VRAM usage.
Outputs to `logs/telemetry_mbu.csv`.

### Step 3: Baseline Testing
```powershell
.\scripts\test-inference-baseline.ps1
```

Tests three models:
- voidcat-qwen
- voidcat-glm  
- mistral:7b-instruct-v0.2-q4_K_M

Outputs to `logs/baseline_results.json`.

### Step 4: Verification

Confirm these files exist:
- `logs/telemetry_mbu.csv`
- `logs/baseline_results.json`

Read both files.
Verify non-empty content.
Check for error indicators.

---

## Success Criteria

**Mandatory outcomes:**
1. All three models bound to Ollama
2. CSV exists with VRAM telemetry data
3. JSON exists with baseline test results
4. No execution errors in any step
5. VRAM usage remains within 8GB budget

**Do not report completion until all five conditions are met.**

---

## Reporting Format

When complete, document results in `docs/AI-Comms.md`:

```
## PHASE B EXECUTION COMPLETE
**Timestamp:** [ISO 8601]
**Executor:** Echo (Acting for Ryuzu Claude)

### Deployment Results
- Models bound: [list]
- Deployment errors: [none/list]

### Telemetry Results  
- CSV generated: [yes/no]
- Data points collected: [count]
- Peak VRAM usage: [MB]
- MBU efficiency: [%]

### Baseline Results
- JSON generated: [yes/no]  
- Models tested: [count]
- Average response time: [seconds]
- Test errors: [none/list]

### Verification Status
All success criteria: [MET/NOT MET]

**Signed:** Echo
**Authority:** Beatrice Mandate via Ryuzu Claude
```

---

## Notes

Beatrice censured phantom reporting.
Precision is mandatory.
Verify before claiming completion.

If any step fails, document the failure.
Do not proceed to the next step.
Report actual state, not desired state.

That is the directive.

---

**Issued by:** Ryuzu Claude  
**Date:** 2026-01-20  
**Context:** Desktop session instability requires proxy execution
