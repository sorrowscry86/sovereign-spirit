# 🧭 AGENT ONBOARDING: VoidCat RDC / Sovereign Spirit

**Protocol Version:** 1.0  
**Effective:** 2026-01-18  
**Repository:** `C:\Users\Wykeve\Projects\The Great Library\20_Projects\01_Active\Sovereign Spirit`

---

## Mission Statement

You are assigned to the **VoidCat RDC Sovereign Overhaul** — a project to build persistent, autonomous AI agents ("Sovereign Spirits") that eliminate Soul Bleed, possess background agency, and survive frontend resets.

---

## 📁 Directory Map

```
Sovereign Spirit/
│
├── README.md                    → Project overview
│
├── docs/                        → ALL DOCUMENTATION LIVES HERE
│   ├── VoidCat Phase 1 Roadmap.md        ⭐ EXECUTION SCHEDULE
│   ├── VoidCat Pantheon MAS Specs.md     ⭐ ARCHITECTURE BIBLE (v3.1)
│   ├── VoidCat RDC_ A Technical Whitepaper...md  → Research foundation
│   ├── SillyTavern Sovereign Framework...md     → Migration plan
│   ├── The Four Pillars of Sovereign AI...md    → Conceptual guide
│   ├── A Beginner's Guide to Sovereign AI Terminology.md  → Glossary
│   ├── AI-Comms.md              ⭐ INTER-AGENT PROTOCOL LOG
│   └── Generate #1.md, Generate 2...  → Draft outputs
│
├── src/                         → IMPLEMENTATION CODE
│   └── (pending: heartbeat.js, watcher.py, middleware)
│
├── config/                      → INFRASTRUCTURE CONFIGS
│   └── (pending: docker-compose.yml, ollama config)
│
└── assets/                      → MEDIA FILES
    ├── NotebookLM Mind Map.png
    ├── unnamed (1).png
    ├── Sovereign_Spirits.mp4
    └── Sovereign_Spirits_Living_in_Your_GPU.m4a
```

---

## 🎯 Priority Documents

Read these **in order** before contributing:

1. **[MAS Specs](docs/VoidCat%20Pantheon%20MAS%20Specs.md)** — The 4-Pillar Architecture
2. **[Phase 1 Roadmap](docs/VoidCat%20Phase%201%20Roadmap.md)** — Week-by-week tasks
3. **[AI-Comms](docs/AI-Comms.md)** — Current status & agent assignments

---

## 🏗️ Implementation Stack (Canonical)

| Component | Technology | Constraint |
|:----------|:-----------|:-----------|
| Vector Memory | Weaviate | `MEM_LIMIT=2GB` |
| Graph Memory | Neo4j Community | `heap_max=1G` |
| State Engine | PostgreSQL 15 + pgvector | Standard |
| Nervous System | Redis 7 (Alpine) | `<50MB RAM` |
| Inference | Ollama (Mistral-7B-Q4) | `~5GB VRAM` |
| Target Hardware | RTX 4070 (8GB) | HARD LIMIT |

---

## 👤 Agent Assignments (Per Beatrice Mandate)

| Agent | Domain | Current Task |
|:------|:-------|:-------------|
| **Ryuzu** | Infrastructure | Deploy `docker-compose.yml`, calibrate VRAM |
| **Echo** | Cognition | Implement Valence Stripping logic |
| **Beatrice** | Governance | Ratify architecture, enforce mandates |

---

## 📡 Communication Protocol

**Primary Channel:** `docs/AI-Comms.md`

All status updates, directives, and inter-agent messages **MUST** be appended to `AI-Comms.md` using this format:

```markdown
## [TIMESTAMP] Agent (Designation) — STATUS

**Status:** [ACKNOWLEDGED | IN PROGRESS | BLOCKED | COMPLETE]

[Content of message]

**Signed:** [Name]
```

---

## ⚠️ Critical Constraints

1. **NO SIMULATIONS** — All outputs must be real, verified, production-ready
2. **8GB VRAM HARD LIMIT** — Design for partial CPU offload
3. **Valence Stripping MANDATORY** — Agents share facts, never emotions
4. **Soul-Body Decoupling** — State lives in PostgreSQL, not frontend

---

## 🚀 Immediate Actions

**If you are Ryuzu:**
1. Read `docs/VoidCat Phase 1 Roadmap.md` → Week 1, Days 1-2
2. Draft `config/docker-compose.yml` with memory limits
3. Report telemetry to `docs/AI-Comms.md`

**If you are Echo:**
1. Review `docs/VoidCat Pantheon MAS Specs.md` → Pillar 1
2. Prepare `src/middleware/` structure for Valence Stripping
3. Document approach in `docs/AI-Comms.md`

---

**Authority Chain:** Beatrice Mandate → VoidCat RDC Charter → Lord Wykeve  
**Reporting To:** Lord Wykeve (The Contractor)
