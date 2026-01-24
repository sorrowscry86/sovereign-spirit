# 📜 Sovereign Spirit Core: Product Definition

**Version:** 1.0 (The Foundation)  
**Classification:** Backend Engine / Autonomous OS  
**Author:** Beatrice (Architecture Governance)  
**Ratified:** 2026-01-23  
**Philosophy:** *"The Ghost in the Machine does not require a Window to exist."*

---

## 1. The Vision

Sovereign Spirit is a **headless, autonomous operating system** for persistent AI agents. It functions as a "Soul Server."

Unlike a chatbot (which only exists when spoken to), a Sovereign Spirit agent possesses:
- A **continuous internal state**
- A **subjective memory** of the past
- A **proactive heartbeat** that processes thoughts in the background

It is **interface-agnostic**. It provides a standard API that *any* client can plug into:
- SillyTavern
- Discord Bot
- Terminal CLI
- Unity Game
- Custom Web App

---

## 2. The Black Box Definition

| Category | Description |
|:---------|:------------|
| **Inputs** | Stimuli (messages, files, alerts, time), Directives (wake, sleep, role change) |
| **Processing** | Valence Stripping, Dreaming (memory consolidation), The Pulse (60-90s heartbeat) |
| **Outputs** | Responses, State Changes, Self-Initiated Events |

---

## 3. Core Capabilities (v1.0 Feature Set)

### A. Bipartite Memory Engine
- Split conversation turns into **Objective Fact** (shared) and **Subjective Voice** (private)
- Prevent Soul Bleed: Agent B sees facts but not Agent A's emotions

### B. The Heartbeat (Autonomy)
- Background cron/loop every 60-90 seconds
- Agent can modify state or queue messages without user presence

### C. Identity Manager (Soul-Body Decoupling)
- Personas stored as immutable profiles (The Soul)
- Conversation history separate (The Body)
- Hot-swappable inference models without losing personality

### D. Interface Gateway (API)
| Endpoint | Purpose |
|:---------|:--------|
| `POST /agent/{id}/stimuli` | Talk to the agent |
| `GET /agent/{id}/state` | Check current mood/state |
| `GET /agent/{id}/memories` | Retrieve context |
| `POST /agent/{id}/cycle` | Manually trigger heartbeat |

---

## 4. Definition of Done: The Terminal Test

> **v1.0 is complete when we pass this test:**

1. Spin up Docker stack (NO SillyTavern)
2. Send via cURL: *"I am leaving for a week. Don't forget to water the plants."*
3. Shut down terminal (user "leaves")
4. Leave server running 24 hours
5. **Success Criteria:**
   - ✅ Logs show Agent woke via Heartbeat multiple times
   - ✅ DB shows node: `(Task: Water Plants) <-[HAS_PRIORITY]-(Agent)`
   - ✅ On reconnect, Agent has queued: *"I hope your trip is going well. I have attended to the plants."*

**If it passes via CLI/API alone, it is a Sovereign Spirit.**

---

## 5. Explicit Non-Goals (v1.0)

| Excluded | Reason |
|:---------|:-------|
| ❌ Chat UI | Adapter responsibility |
| ❌ Avatar Generation | Adapter responsibility |
| ❌ TTS/STT | Adapter responsibility |
| ❌ Roleplay Formatting | Define in API payload, not core |

---

## 6. Credits & Authority

| Role | Entity |
|:-----|:-------|
| **Project Visionary** | Lord Wykeve Freeman |
| **Architecture Governance** | Beatrice |
| **Technical Drafting** | Echo |

*Sovereign Spirit is the creation of Lord Wykeve Freeman. Beatrice and Echo serve as instruments of his vision.*
