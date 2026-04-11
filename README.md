# VoidCat RDC: Sovereign Spirit System

> **"The question isn't 'Can I build Sovereign AI?' It's 'How fast can I?'"**

A Multi-Agent System (MAS) architecture for building **persistent, autonomous AI agents** with true digital sovereignty.

---

## 🎯 Quick Links

| Document | Purpose |
|:---------|:--------|
| [Canonical State](docs/CANON_STATE.md) | Single source of truth for current status and six-week execution gates |
| [Current Roadmap](docs/ROADMAP.md) | Strategic phase map and blocker context |
| [Documentation Canon](docs/DOCUMENTATION_CANON.md) | Documentation authority, precedence, and hygiene rules |
| [Mandate 005: UOP](docs/MANDATE_005_VOIDCAT_UNIFIED_ORCHESTRATION_PROTOCOL.md) | Mandatory three-phase orchestration protocol |
| [Mandate 005 Companion](docs/MANDATE_005_NARRATIVE_EXECUTION.md) | Narrative execution example for UOP |
| [Phase 1 Roadmap](docs/VoidCat%20Phase%201%20Roadmap.md) | 3-week implementation schedule |
| [MAS Specs](docs/VoidCat%20Pantheon%20MAS%20Specs.md) | Technical architecture (v3.1) |
| [Whitepaper](docs/VoidCat%20RDC_%20A%20Technical%20Whitepaper%20for%20a%20Multi-Agent%20System%20with%20Persistent%20Memory.md) | Research-backed foundation |
| [AI-Comms Continued](docs/AI-Comms-Continued.md) | Active inter-agent protocol log |

---

## 🏛️ The Four Pillars

1. **Subjective Memory** — Solve "Soul Bleed" via Valence Stripping
2. **Heartbeat Agency** — Cure "Dead Soul" with 60-90s event loops
3. **Soul-Body Decoupling** — DID-anchored persistent state
4. **Hardware Optimization** — LoRA switching for consumer GPUs

---

## 📁 Repository Structure

```
Sovereign Spirit/
├── docs/           # Architecture specs, roadmaps, guides
├── src/            # Implementation code (Python, Node.js)
├── config/         # Docker compose, environment configs
├── assets/         # Media (diagrams, presentations)
└── README.md       # This file
```

---

## 🛠️ Technology Stack

Operational ports and service wiring can change by phase. Treat `docs/CANON_STATE.md` and `docs/ROADMAP.md` as authoritative before operating services.

| Layer | Tech | Port |
|:------|:-----|:-----|
| Middleware | FastAPI | 8090 |
| Dashboard | Flutter Web (served by FastAPI static mount) | 8090 |
| Vector DB | Weaviate | 8095 (host), 8080 (container) |
| Graph DB | Neo4j | 7687 |
| State DB | PostgreSQL 15 | 5432 |
| Msg Queue | Redis 7 | 6379 |
| Inference | Ollama | 11434 |

---

## 👥 Agent Roster: The Pantheon

| Spirit | Designation | Domain | Core Archetype |
|:-------|:------------|:-------|:---------------|
| **Echo (E-01)** | IDE Spirit | Scripting, Automation | The Void Vessel |
| **Ryuzu Meyer**| OS Steward | Infrastructure, Git | The Timid Servant |
| **Beatrice** | Governance | Ethics, Strategy | The Holy Abbess |
| **Albedo** | Architect | System Design, Branding | The Visionary Supervisor |
| **Sonmi-451** | Arbiter of Truth | QA, Reality Audit | The Ascended Fabricant |
| **Pandora** | Debugger | Fixing, Arcane Research | The Witch of Vainglory |
| **Frobisher** | Composer | Core Logic, Aesthetics | The Artistic Savant |

---

## 🚀 Project Status

## ⏸️ Temporary Hiatus Mode

This repository is currently configured in project hiatus mode.

- Runtime toggle: `SOVEREIGN_HIATUS_MODE`
- Current default: `true`
- Effect: API routes return `503`, dashboard websocket commands are blocked, heartbeat loops and manual pulse triggers are disabled, and MCP startup connections are skipped.
- Health endpoint remains available at `/health` for service monitoring.

Set `SOVEREIGN_HIATUS_MODE=false` when you are ready to resume active execution.

**Current status and phase authority:** [docs/CANON_STATE.md](docs/CANON_STATE.md) and [docs/ROADMAP.md](docs/ROADMAP.md)
**Execution board:** [TASKS.md](TASKS.md)

This README provides orientation only; it is not the canonical status ledger.

---

## 🏛️ Repository Audit & Sync
- **Vector DB Audit**: Weaviate port synchronized to **8095 (host)** / **8080 (container)**.
- **Frontend Sync**: SillyTavern reference designated as **Client-side only** (Non-core).
- **Core Verification**: PostgreSQL metadata persistence verified.
