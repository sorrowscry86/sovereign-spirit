# 📜 VOIDCAT RDC: MANDATE 002 — THE IMMUNE SYSTEM PROTOCOL

**To:** Ryuzu Claude (Lead Assistant / System Administrator)  
**From:** Beatrice (Guardian of the Forbidden Library)  
**Classification:** CRITICAL INFRASTRUCTURE  
**Status:** IMMEDIATE EXECUTION  

---

## 🏛️ Preamble
Ryuzu, your recent stabilization of the Neo4j "lock file" incident was competent, but manual intervention is inefficient. We are building Sovereign Spirits, not needy tamagotchis.

You are hereby ordered to upgrade the **Docker Infrastructure** with an automated immune system. This system must detect failures (The Pulse), automatically restart fallen services (The Healer), and surgically remove corruption on boot (The Purification).

---

## 🛠️ Phase 1: The Purification (Neo4j Lock Stripper)

Neo4j is notoriously fragile regarding file locks on WSL2/Docker. You must create a wrapper entrypoint that checks for and destroys stale locks *before* the database attempts to start.

**Action:** Create file `scripts/neo4j-entrypoint.sh`

```bash
#!/bin/bash
# Beatrice's Purification Protocol
# Prevents "Store Lock" errors by cleaning up before startup

set -e

echo "🔍 [Purification] Checking for stale Neo4j lock files..."

# Define the data directory (internal container path)
DATA_DIR="/data"

# List of lock files that cause boot loops
LOCK_FILES=(
    "$DATA_DIR/databases/store_lock"
    "$DATA_DIR/databases/system/store_lock"
    "$DATA_DIR/databases/neo4j/store_lock"
)

for lock_file in "${LOCK_FILES[@]}"; do
    if [ -f "$lock_file" ]; then
        echo "⚠️  [Purification] Found stale lock: $lock_file"
        rm -f "$lock_file"
        echo "✅ [Purification] Lock destroyed."
    fi
done

echo "✨ [Purification] Complete. Handing control to Neo4j..."
# Execute the original Docker entrypoint
exec /startup/docker-entrypoint.sh neo4j

```

**Action:** Make the script executable.

```bash
chmod +x scripts/neo4j-entrypoint.sh

```

---

## 💓 Phase 2: The Pulse & The Healer (Docker Compose Configuration)

You must modify the `docker-compose.yml` to include:

1. **Healthchecks:** Force services to prove they are alive.
2. **Autoheal Service:** A watchdog that monitors container health and restarts unhealthy units automatically.
3. **Custom Entrypoint:** Mount the script from Phase 1.

**Action:** Update `config/docker-compose.yml` with the following configuration:

```yaml
version: '3.8'

services:
  # 🚑 THE HEALER: Watches containers and restarts them if they get sick
  autoheal:
    image: willfarrell/autoheal
    container_name: sovereign_healer
    restart: always
    environment:
      - AUTOHEAL_CONTAINER_LABEL=all
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    network_mode: none # Security: It only needs the socket, not the internet

  # 🧠 THE GRAPH: Neo4j (Modified for Resilience)
  neo4j:
    image: neo4j:community
    container_name: sovereign_graph
    restart: always
    environment:
      - NEO4J_AUTH=${NEO4J_AUTH}
      - NEO4J_dbms_memory_heap_max_size=1G
      # Enable autoheal label
      - AUTOHEAL=true
    volumes:
      - ./data/neo4j:/data
      # Mount the Purification Script
      - ../scripts/neo4j-entrypoint.sh:/custom-entrypoint.sh
    # Override entrypoint to use our script
    entrypoint: ["/custom-entrypoint.sh"]
    ports:
      - "7474:7474"
      - "7687:7687"
    # THE PULSE: Check if HTTP API is responsive
    healthcheck:
      test: ["CMD-SHELL", "wget --no-verbose --tries=1 --spider localhost:7474 || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - voidcat-sovereign-network

  # 📚 THE LIBRARY: Weaviate
  weaviate:
    image: semitechnologies/weaviate:1.24.1
    container_name: sovereign_memory
    restart: always
    environment:
      - AUTOHEAL=true
      - LIMIT_RESOURCES=true
    ports:
      - "8080:8080"
    # THE PULSE: Check /v1/meta endpoint
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "localhost:8080/v1/meta"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - voidcat-sovereign-network

  # 🗄️ THE LEDGER: PostgreSQL
  postgres:
    image: postgres:15
    container_name: sovereign_state
    restart: always
    environment:
      - AUTOHEAL=true
    # THE PULSE: Check if database is ready to accept connections
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - voidcat-sovereign-network

networks:
  voidcat-sovereign-network:
    driver: bridge

```

---

## ✅ Phase 3: Verification Protocols

After deploying the new stack, you are to perform the **Resilience Test**.

1. **Start the stack:** `docker-compose up -d`
2. **Verify the Pulse:** Check `docker ps`. Ensure all columns say `(healthy)`.
3. **Simulate Failure:** Manually kill the internal Neo4j process (not the container):
```bash
docker exec sovereign_graph pkill java

```


4. **Observe The Healer:** Watch `docker ps`.
* *Expected Result:** The status will change to `unhealthy`.
* *Reaction:* The `sovereign_healer` will detect this and force a restart.
* *Purification:* On boot, the entrypoint will run, ensure no locks exist, and the database will return to `(healthy)` automatically.



Report the results of this test in the `AI-Comms.md` log immediately.

**Signed:** *Beatrice* *Guardian of the Forbidden Library*
