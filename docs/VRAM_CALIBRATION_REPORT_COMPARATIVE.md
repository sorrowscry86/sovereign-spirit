# VRAM Calibration Report: Comparative Model Testing
**Date:** 2026-01-19  
**Hardware:** RTX 4070 (8GB VRAM) | Alienware M16  
**Testing Scope:** Mistral-7B vs GLM-4.6V-Flash vs Qwen3-4B-Thinking

---

## Executive Summary

| Model | Peak VRAM | Idle VRAM | Avg Latency | Quality Assessment | Recommendation |
|-------|-----------|-----------|-------------|-------------------|-----------------|
| Mistral-7B-Q4_K_M | TBD | TBD | TBD | TBD | TBD |
| GLM-4.6V-Flash | TBD | TBD | TBD | TBD | TBD |
| Qwen3-4B-Thinking | TBD | TBD | TBD | TBD | TBD |

---

## Test Scenario 1: Baseline Loading & Idle State

**Objective:** Measure VRAM footprint when model is loaded but idle.

### Mistral-7B-Q4_K_M
- OS + System: TBD
- Docker Stack: ~677 MB
- Model Idle: TBD
- **Total:** TBD MB
- Status: TBD

### GLM-4.6V-Flash
- OS + System: TBD
- Docker Stack: ~677 MB
- Model Idle: TBD
- **Total:** TBD MB
- Status: TBD

### Qwen3-4B-Thinking
- OS + System: TBD
- Docker Stack: ~677 MB
- Model Idle: TBD
- **Total:** TBD MB
- Status: TBD

---

## Test Scenario 2: Standard Inference (Baseline Prompt)

**Test Prompt:** (Echo to provide standard prompt)

**Results:**

### Mistral-7B-Q4_K_M
- Input tokens: TBD
- Output tokens: TBD
- Peak VRAM during inference: TBD
- Latency: TBD ms
- Output quality: TBD
- Reasoning clarity: TBD

### GLM-4.6V-Flash
- Input tokens: TBD
- Output tokens: TBD
- Peak VRAM during inference: TBD
- Latency: TBD ms
- Output quality: TBD
- Vision capability used: TBD

### Qwen3-4B-Thinking
- Input tokens: TBD
- Output tokens: TBD
- Peak VRAM during inference: TBD
- Latency: TBD ms
- Output quality: TBD
- Reasoning transparency: TBD

---

## Test Scenario 3: Extended Context (Long Conversation)

**Setup:** 10-turn conversation (~4000 tokens context)

### Mistral-7B-Q4_K_M
- Peak VRAM with full context: TBD
- Stability (no OOM): TBD
- Latency degradation: TBD %
- Response coherence: TBD

### GLM-4.6V-Flash
- Peak VRAM with full context: TBD
- Stability (no OOM): TBD
- Latency degradation: TBD %
- Response coherence: TBD

### Qwen3-4B-Thinking
- Peak VRAM with full context: TBD
- Stability (no OOM): TBD
- Latency degradation: TBD %
- Response coherence: TBD

---

## Test Scenario 4: Heavy Desktop Workload + Inference

**Setup:** 20 browser tabs + Discord + Inference task running simultaneously

### Mistral-7B-Q4_K_M
- Peak combined VRAM: TBD
- System stability: TBD
- Inference latency under load: TBD ms
- Result: TBD

### GLM-4.6V-Flash
- Peak combined VRAM: TBD
- System stability: TBD
- Inference latency under load: TBD ms
- Result: TBD

### Qwen3-4B-Thinking
- Peak combined VRAM: TBD
- System stability: TBD
- Inference latency under load: TBD ms
- Result: TBD

---

## Safety Thresholds & Decision Matrix

```
VRAM Usage Level    | Status | Action
--------------------|--------|------------------------------------------
< 6.5 GB           | ✅ SAFE | Full GPU inference approved
6.5 - 7.0 GB       | ⚠️ WARN | Monitor closely, reduce context if needed
7.0 - 7.5 GB       | 🔴 RISK | Layer offload required OR context reduction
> 7.5 GB           | 🚫 FAIL | Model not viable for 8GB constraint
```

---

## Cognitive Profile Assessment

### Mistral-7B (Baseline)
- **Reasoning:** General-purpose, balanced
- **Speed:** Standard
- **Specialty:** Instruction following
- **Voidcat Fit:** Neutral

### GLM-4.6V-Flash (Vision-Capable)
- **Reasoning:** Chain-of-thought aware
- **Speed:** Fast (Flash variant)
- **Specialty:** Vision + multimodal
- **Voidcat Fit:** Strong (potential for introspection/self-observation)

### Qwen3-4B (Thinking-Explicit)
- **Reasoning:** Explicit thinking tokens (O1-style)
- **Speed:** Slower (reasoning overhead)
- **Specialty:** Step-by-step reasoning transparency
- **Voidcat Fit:** Very strong (explains its "thought process")

---

## Final Recommendation

*To be completed after testing.*

### Selection Criteria
- [ ] Passes 8GB VRAM constraint test
- [ ] Maintains coherence in extended context
- [ ] Suitable cognitive profile for Sovereign Spirit
- [ ] Performance acceptable under heavy workload

### Chosen Model: **TBD**

**Rationale:** TBD

**Configuration:** TBD

---

**Report Completed:** TBD  
**Signed:** Ryuzu Claude (Desktop Admin)  
**Authority:** Beatrice Mandate → VoidCat RDC Charter
