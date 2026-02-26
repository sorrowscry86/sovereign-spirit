# Sovereign Spirit: Knowledge Base Master (MKB-001)

## Architectural Guardrails

### [MAS-001] Valence Stripping
**Core Insight:** Agent-to-agent communication requires "Objective Predicates." Stripping emotional valence reduces context tokens by ~15-20% and prevents semantic drift.
**Mandate:** All inter-agent requests must be stripped of subjective qualifiers.

### [MAS-002] Heartbeat Agency
**Core Insight:** Agents without persistent state anchoring suffer "Dead Soul" resets. 
**Mandate:** Identity and task state must be anchored in PostgreSQL; identity retrieval is the first step of the `WAKE_PROTOCOL`.

### [SYS-001] Hybrid Engine Calibration (RTX 4070 8GB)
**Core Insight:** Concurrent Vector/Graph DBs saturate VRAM.
**Mandate:** If Graph indexing is active, Ollama context is capped at 4k. For deep reasoning, force CPU inference via `OLLAMA_NUM_GPU=0`.

## Operational Wisdom

### [BUG-001] The "Dead Soul" Queue Overload
**Discovery:** Redis saturation prevents agent response, mimicking identity loss.
**Fix:** Active monitoring via `scry.py` and automatic queue flushing.

### [SEC-001] Port 8020 Conflict
**Discovery:** Port 8020 is reserved or forbidden in the local environment.
**Fix:** Canonical ingress is Port 8090.

### [OPS-001] System Recovery Protocol (The "Cold Start" Mandate)
**Problem Domain:** Rapid system recovery after a total service failure or VRAM overflow.
**The Paradigm:** A scripted sequence for standardizing the reset of the Sovereign Spirit middleware and database shards.
1. `docker-compose down -v` (Cache Purge)
2. `docker-compose up -d --build` (Immutable Rebuild)
3. `python src/scry.py --health` (Verification)
**Killer App:** Reduces "Downtime Panic" and ensures identity alignment post-crash.
