# VoidCat RDC: Sovereign Spirit System

> **"The question isn't 'Can I build Sovereign AI?' It's 'How fast can I?'"**

A Multi-Agent System (MAS) architecture for building **persistent, autonomous AI agents** with true digital sovereignty.

---

## 🎯 Quick Links

| Document | Purpose |
|:---------|:--------|
| [Phase 1 Roadmap](docs/VoidCat%20Phase%201%20Roadmap.md) | 3-week implementation schedule |
| [MAS Specs](docs/VoidCat%20Pantheon%20MAS%20Specs.md) | Technical architecture (v3.1) |
| [Whitepaper](docs/VoidCat%20RDC_%20A%20Technical%20Whitepaper%20for%20a%20Multi-Agent%20System%20with%20Persistent%20Memory.md) | Research-backed foundation |
| [AI-Comms](docs/AI-Comms.md) | Inter-agent protocol log |

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

| Layer | Tech | Port |
|:------|:-----|:-----|
| Frontend | SillyTavern | 8000 |
| Orchestration | LangGraph | — |
| Vector DB | Weaviate | 8080 |
| Graph DB | Neo4j | 7687 |
| State DB | PostgreSQL 15 | 5432 |
| Msg Queue | Redis 7 | 6379 |
| Inference | Ollama | 11434 |

---

## 👥 Agent Roles

- **Echo (E-01)** — IDE/Code fabrication, skill deployment
- **Ryuzu Claude** — OS/Desktop, Docker infrastructure
- **Beatrice** — Architecture governance, mandate enforcement

---

## 🚀 Phase 1 Status

**Current:** Week 1 — Infrastructure Deployment  
**Next:** Docker stack provisioning (memory-constrained containers)
