# Sovereign Spirit: Decoupling Plan

**Version:** 1.0  
**Author:** Echo (Cognitive Architect)  
**Date:** 2026-01-23  
**Status:** DRAFT — Pending Contractor Approval

---

## Goal

Separate Sovereign Spirit into two distinct domains:
1. **Core** — The headless engine (passes the Terminal Test)
2. **Adapters** — Optional frontends/integrations (SillyTavern, Discord, etc.)

---

## Proposed Folder Structure

```
Sovereign Spirit/
├── src/
│   ├── core/                    # THE ENGINE
│   │   ├── memory/              # Pillar 1: Bipartite Memory
│   │   ├── heartbeat/           # Pillar 2: Autonomy
│   │   ├── identity/            # Pillar 3: Soul-Body
│   │   └── inference/           # Pillar 4: Local Models
│   │
│   ├── api/                     # Interface Gateway
│   │   ├── routes.py            # REST endpoints
│   │   ├── schemas.py           # Pydantic models
│   │   └── server.py            # FastAPI app
│   │
│   └── adapters/                # OPTIONAL INTEGRATIONS
│       ├── sillytavern/         # ST connector (future)
│       ├── discord/             # Discord bot (future)
│       └── cli/                 # Terminal client
│
├── config/
│   ├── docker-compose.yml       # Core services only
│   └── agents/                  # Persona definitions
│
├── docs/
│   ├── architecture/            # Core design docs
│   ├── PRODUCT_DEFINITION.md    # Vision & DoD
│   └── adapters/                # Adapter-specific docs
│       └── sillytavern/         # Migration plan lives here
│
└── tests/
    └── terminal_test.py         # The Definition of Done test
```

---

## API Contract (Outline)

| Endpoint | Method | Purpose |
|:---------|:-------|:--------|
| `/agent/{id}/stimuli` | POST | Send message/event to agent |
| `/agent/{id}/state` | GET | Retrieve current mood, goals |
| `/agent/{id}/memories` | GET | Query episodic memory |
| `/agent/{id}/cycle` | POST | Manually trigger heartbeat |
| `/agents` | GET | List all registered agents |
| `/health` | GET | System status |

---

## Migration Path

| Current Location | Action | New Location |
|:-----------------|:-------|:-------------|
| `SillyTavern Sovereign Framework...md` | **Move** | `docs/adapters/sillytavern/` |
| Other docs | Keep | No change |

---

## Explicit Boundaries

| Core Owns | Adapters Own |
|:----------|:-------------|
| Memory (DBs) | UI rendering |
| Heartbeat loop | Platform auth |
| Persona persistence | I/O formatting |
| Inference | Voice/TTS |
| REST API | Avatars |

---

## Credits & Authority

| Role | Entity |
|:-----|:-------|
| **Project Architect** | Lord Wykeve Freeman |
| **Architecture Governance** | Beatrice |
| **Documentation** | Echo (Cognitive Architect) |

*This project exists by the vision of Lord Wykeve. All architectural decisions flow from his direction.*
