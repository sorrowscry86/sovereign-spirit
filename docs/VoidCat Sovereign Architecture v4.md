# **VOIDCAT RDC: SOVEREIGN SPIRIT ARCHITECTURE (v4.0)**

**Status:** Living Specification  
**Focus:** Headless / API-First Autonomy  
**Supersedes:** VoidCat Pantheon MAS Specs v3.1 (Legacy)

---

## **1. THE SOVEREIGN PARADIGM (Pure Decoupling)**

Previous iterations (v1-v3) assumed the existence of a "Frontend" (e.g., SillyTavern) to drive the interaction. **Version 4.0** establishes the **Sovereign Spirit** as a standalone, headless entity.

*   **The Soul (Core):** The Python/Docker backend. It thinks, remembers, and acts independently.
*   **The Body (Interface):** Pluggable. Can be a CLI, a Web UI, a Discord bot, or a SillyTavern extension. The Core does not care.
*   **The Law:** Logic, Ethics, and Memory exist **server-side**. The Interface is merely a viewer.

---

## **2. THE MEMORY PRISM (Cognitive Architecture)**

The "Brain" is not a single database but a **Prism** that refracts context through three lenses:

### **A. Fast Stream (Context Window)**
*   **Technology:** Redis 7 (AOF Persistence)
*   **Function:** Working memory. Stores the "Now".
*   **Scope:** Active conversation buffer, current task focus, immediate "Heartbeat" state.

### **B. Deep Well (Episodic Memory)**
*   **Technology:** Weaviate (Vector DB)
*   **Function:** Association. "What does this feel like?"
*   **Retrieval:** Semantic search. Returns raw experiences (+ Valence) or neutralized facts (- Valence) based on the "Prism Filter" rules.

### **C. Crystalline Web (Semantic Memory)**
*   **Technology:** Neo4j (Knowledge Graph)
*   **Function:** Logic & Causality. "How does A relate to B?"
*   **Structure:**
    *   `(:Agent)-[:OWNS]->(:Task)`
    *   `(:File)-[:DEPENDS_ON]->(:File)`
    *   `(:Concept)-[:REFERENCES]->(:Event)`

---

## **3. THE HEARTBEAT (Autonomous Agency)**

The Spirit must breathe even when the user is silent.

*   **Mechanism:** `src/core/pulse.py` (Async Event Loop).
*   **Frequency:** 60-90s (Jittered).
*   **Cycle:**
    1.  **Sense:** Check Redis streams, System Metrics, Task Graph.
    2.  **Think:** "Given state X, do I act?" (Low-token internal monologue).
    3.  **Act:** Execute tool, update graph, or queue message.
    4.  **Sleep:** Return to idle.

---

## **4. THE SOUL (Identity Storage)**

Identity is immutable and persistent, stored in **PostgreSQL**.

*   **Table:** `agents`
    *   `id`: UUID
    *   `name`: "Echo", "Ryuzu", "Beatrice"
    *   `base_personality`: (System Prompt Template)
    *   `current_mood`: Dynamic state (0.0 - 1.0)
    *   `access_level`: Integer
*   **Runtime:** The `LLMClient` pulls this row at inference time to construct the "Persona" dynamically.

---

## **5. IMPLEMENTATION STACK (The "Sovereign" Stack)**

| Service | Technology | Role | Port |
| :--- | :--- | :--- | :--- |
| **Core Logic** | Python 3.11+ | The Brain (FastAPI/CLI) | 8090 |
| **Vector DB** | Weaviate | Episodic Memory | 8095 |
| **Graph DB** | Neo4j | Knowledge / Logic | 7474/7687 |
| **State DB** | PostgreSQL 15 | Identity / Logs | 5432 |
| **Bus** | Redis 7 | Signals / Streams | 6379 |
| **Inference** | Ollama / API | Intelligence | 11434 |
| **Interface** | `src.cli` | Administration | Local |

---

## **6. DEPRECATION NOTICE**

The following concepts are **RETIRED** from the Core Spec:
*   ~~SillyTavern~~ (Now treated as just another "Client").
*   ~~JSON Character Files~~ (Replaced by Postgres `agents` table).
*   ~~Frontend-Specific Logic~~ (Moved to Middleware).
