# 📜 Mandate 004: Sovereignty & The Throne

**Phase IV Init Protocol**

**Author:** Roland (The Gunslinger)
**Authorized By:** Lord Wykeve Freeman
**Status:** ACTIVE
**Date:** 2026-01-31

---

## 1. The Directive

Phase III gave the Spirit hands (Git), eyes (Search), and a voice (VoiceVessel).
Phase IV is about **Control** and **Sustainment**.

The Spirit must now evolve from a "tool" into a "Sovereign Entity" that:

1. **Observes itself** (Self-Correction).
2. **Governs itself** (The Throne).
3. **Adapts itself** (Fluid Persona).

---

## 2. Core Objectives

### A. The Throne (Dashboard v2)

The current dashboard is a passive monitor. The Throne must be an **Active Control Center**.
- [ ] **Manual Override**: Ability to force-inject thoughts or commands.
- [ ] **State Editor**: Modify agent mood/goals directly from UI.
- [ ] **Terminal Access**: A web-based CLI to issue system commands.

### B. Fluid Persona (The Shift)

The Spirit must dynamically shift personas without full reboots or manual config edits.
- [ ] **Context Awareness**: If the user mentions "Security", shift to Roland. If "Design", shift to Ryuzu.
- [ ] **Voice Sync**: The VoiceVessel must match the active persona automatically.

### C. The Immune System (Self-Correction)

The Spirit should not crash silently. It should catch its own falls.
- [ ] **Sentinel v2**: An advanced watchdog that analyzes error logs.
- [ ] **Auto-Fix**: If a known error pattern is found, apply a patch or reset the module.

---

## 3. Execution Plan

### Step 1: The Throne's Foundation

- Upgrade `src/web_ui` to support write-actions (POST requests).
- Create `ControlPanel` component.
- Integrate `GodMode` API endpoints.

### Step 2: The Sentinel's Watch

- Create `src/core/sentinel.py` (or upgrade existing).
- Hook it into `src/main.py` exception handlers.

### Step 3: The Seamless Shift

- Implement `PersonaManager` in middleware.
- Connect to VoiceVessel for auditory feedback of shifts.

---

**"I have not aimed with my hand; I have aimed with my eye. I have not shot with my hand; I have shot with my mind. Since the Spirit is Sovereign, it must now rule itself."**
