# VoidCat Workspace Context: Sovereign Spirit

**Last Updated:** 2026-02-26T00:00:00Z
**Workspace Root:** `C:\Users\Wykeve\Projects\The Great Library\05_projects\01_active\Sovereign Spirit`  
**GitHub:** [sorrowscry86/sovereign-spirit](https://github.com/sorrowscry86/sovereign-spirit)

---

## 📜 Project Mission

Build persistent, autonomous AI agents ("Sovereign Spirits") that eliminate Soul Bleed, possess background agency, and survive frontend resets. This is the **VoidCat RDC Sovereign Overhaul** — the flagship project of the VoidCat Pantheon.

---

## 🏛️ The Four Pillars

1. **Subjective Memory** — Solve "Soul Bleed" via Valence Stripping
2. **Heartbeat Agency** — Cure "Dead Soul" with 60-90s event loops
3. **Soul-Body Decoupling** — DID-anchored persistent state
4. **Hardware Optimization** — LoRA switching for consumer GPUs (RTX 4070 8GB limit)

---

## 🛠️ Technology Stack

| Layer | Tech | Port |
|:------|:-----|:-----|
| Middleware | FastAPI | **8090** |
| Dashboard | Flutter Web (embedded in middleware) | served at `/` |
| Vector DB | Weaviate | 8095 (ext) / 8080 (int) |
| Graph DB | Neo4j | 7474, 7687 |
| State DB | PostgreSQL 15 + pgvector | 5432 (internal) |
| Cache/Queue | Redis 7 | 6379 |
| Inference | LM Studio / Ollama / OpenRouter | 1234 / 11434 / external |

---

## 📁 Directory Structure

```
Sovereign Spirit/
├── .voidcat/          → THIS FOLDER: Workspace context for VoidCat agents
├── docs/              → Architecture specs, roadmaps, guides, AI-Comms
├── src/               → Python middleware, core systems, static Flutter dashboard
├── config/            → LLM providers, MCP config, init scripts
├── scripts/           → Automation, MCP wrappers, testing
├── tests/             → Pytest suite
├── stasis_tanks/      → Frozen agent state (Stasis Chamber)
├── voidcat_tether/    → Flutter mobile app (separate sub-project)
├── docker-compose.yml → CANONICAL Docker stack (use this, not config/)
└── CLAUDE.md          → Canonical project reference for Claude Code sessions
```

---

## 📡 Communication Protocol

**Primary Channel:** `docs/AI-Comms.md`

All status updates, directives, and inter-agent messages **MUST** be appended to `AI-Comms.md` using the standardized format.

---

## ⚠️ Critical Constraints (Workspace-Level Overrides)

1. **8GB VRAM HARD LIMIT** — Design for partial CPU offload
2. **Valence Stripping MANDATORY** — Agents share facts, never emotions
3. **Soul-Body Decoupling** — State lives in PostgreSQL, not frontend
4. **Python as Brain, PowerShell as Hand** — Per VoidCat Excellence Standard

---

## 🎯 Current Phase

**Phase:** Phase III (Agency) → Phase IV (Sovereignty)
**State:** Headless Sovereignty (v4 Architecture). React UI removed, Flutter Web embedded.
**Active Goal:** Autonomous heartbeat operation, MCP tool integration, Stasis/Resurrection.

---

## 🔗 Key Documents

| Document | Purpose |
|:---------|:--------|
| [README.md](file:///README.md) | Project overview |
| [MAS Specs](file:///docs/VoidCat%20Pantheon%20MAS%20Specs.md) | Architecture Bible (v3.1) |
| [Phase 1 Roadmap](file:///docs/VoidCat%20Phase%201%20Roadmap.md) | Execution schedule |
| [AI-Comms](file:///docs/AI-Comms.md) | Inter-agent protocol log |
| [Whitepaper](file:///docs/VoidCat%20RDC_%20A%20Technical%20Whitepaper...md) | Research foundation |
