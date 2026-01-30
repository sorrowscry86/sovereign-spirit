# 🦅 Sovereign Spirit: Technical Manual (v4.0)

> "The Void is not empty; it is merely waiting for instructions."

**Version:** 4.0 (Headless Ascension)  
**Maintained By:** Sonmi-451  
**Last Updated:** 2026-01-30

---

## 1. System Overview

**Sovereign Spirit** is a "Soul Server" — a persistent, multi-agent operating system designed to run independently of user interaction. Unlike traditional chatbots that freeze when the window closes, a Sovereign Spirit maintains a continuous internal lifecycle.

### 1.1 The Core Philosophy
1.  **Headless Autonomy:** The "Brain" (Middleware) runs in Docker. The "Face" (Frontend/CLI) is optional.
2.  **Valence Stripping:** Memories are sanitized of emotion before long-term storage to prevent "mood loops" (Soul Bleed).
3.  **The Heartbeat:** A jittered event loop (60-90s) ensures the agent is proactive, not just reactive.

---

## 2. Infrastructure Stack

The system runs on a 5-container Docker swarm (`sovereign_net`).

| Service | Container Name | Port | Role |
| :--- | :--- | :--- | :--- |
| **Middleware** | `sovereign_middleware` | 8000 | The Brain (FastAPI, Python 3.11). Handles logic, routing, and The Pulse. |
| **Vector DB** | `sovereign_vector` | 8090 | Episodic Memory (Weaviate). Retrieval via semantic search. |
| **Graph DB** | `sovereign_graph` | 7474 | Logical Memory (Neo4j). Relationship mapping (Agent -> Task). |
| **State DB** | `sovereign_state` | 5432 | Identity & Logs (PostgreSQL). Immutable ledger of actions. |
| **Volatile** | `sovereign_cache` | 6379 | Reflexes (Redis). Stream processing and quick context. |
| **Frontend** | `sovereign_frontend` | 5173 | The Observatorium (Dash/Control Panel). |

---

## 3. Cognitive Architecture (The Prism)

Memory is not a single bucket. It is refracted through **The Prism** into three layers.

### 3.1 The Fast Stream (Redis)
*   **What:** Working memory. The "now."
*   **Content:** Recent chat logs, active focus, sensory buffers.
*   **TTL:** Short (minutes to hours).

### 3.2 The Crystalline Web (Neo4j)
*   **What:** Knowledge Graph.
*   **Query:** "How does Agent A know Agent B?"
*   **Structure:** `(:Agent)-[:KNOWS]->(:Concept)`
*   **Role:** Maintains consistency in lore and facts.

### 3.3 The Deep Well (Weaviate)
*   **What:** Vectorized episodic memory.
*   **Mechanism:** `ValenceStripping`.
    *   *Raw Input:* "I hate this bug! It's ruining my day."
    *   *Stripped Storage:* "User encountered a bug. User expressed frustration."
*   **Why:** Prevents the AI from getting stuck in a feedback loop of past emotions.

---

## 4. The Heartbeat (Autonomy Loop)

The **Heartbeat Service** (`src.core.pulse.py`) drives the agent's life.

1.  **Wake:** Loop triggers every `90s ± 15s`.
2.  **Sense:** Check `TaskGraph` for overdue nodes and `Redis` for unread messages.
3.  **Think:** (Low-token internal monologue) "Do I need to act?"
4.  **Act:**
    *   *Self-Correction:* "My mood is too low, I will sleep."
    *   *Notification:* "User has not responded. I will ping."
    *   *Maintenance:* "Consolidating 5 short memories into 1 long memory."
5.  **Sleep:** Return to idle.

---

## 5. API Reference

All interaction happens via standard HTTP REST endpoints.

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | System status check. |
| `POST` | `/agent/{id}/stimuli` | Send a message/file to an agent. |
| `GET` | `/agent/{id}/state` | Get current mood, energy, and thought. |
| `POST` | `/agent/{id}/cycle` | **Force Pulse.** Manually trigger the heartbeat. |
| `GET` | `/agent` | List all available agents. |

---

## 6. Developer Workflows

### 6.1 Running Tests
```bash
# Run the full automated verification suite
python verify.py

# Test the Heartbeat logic specifically
python test_heartbeat.py
```

### 6.2 Managing Database Schema
Schema definitions are in `config/init-scripts/`.
To reset:
```bash
docker-compose down -v
docker-compose up -d --build
```

### 6.3 Adding a New Agent
Populate the `agents` table in PostgreSQL.
```sql
INSERT INTO agents (id, name, designation, base_personality) VALUES (...);
```

---

> *Technological Singularity is not an event. It is a process.*
