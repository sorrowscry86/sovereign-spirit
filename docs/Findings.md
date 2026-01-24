# Sovereign Spirit: Technical Findings & Learnings

**Purpose:** A log of "GOTCHAs", bugs, and architectural discoveries made during the development process. To prevent backtracking and regression.

---

## **1. Connectivity & Networking**

### **Neo4j on Docker (Localhost Routing)**
*   **Issue:** Connecting to Neo4j Container from Host via `neo4j://localhost:7687` fails with DNS resolution error.
*   **Cause:** The `neo4j://` scheme attempts to route to the cluster members (internal IPs), which the host cannot resolve.
*   **Solution:** Force the `bolt://` scheme when connecting via localhost. This bypasses routing and connects directly to the single instance.
*   **Code Implementation:**
    ```python
    # In health_menu.py fallback
    local_uri = "bolt://localhost:7687"
    ```

### **Docker Ports on Windows**
*   **Finding:** Applications running on the Windows Host (like the CLI) CANNOT access Docker internal IPs.
*   **Requirement:** Ports MUST be explicitly exposed in `docker-compose.yml`.
    *   Postgres: 5432
    *   Redis: 6379
    *   Neo4j: 7474, 7687
    *   Weaviate: 8090 (To avoid 8080 conflict with Middleware)

---

## **2. Python & Dependencies**

### **Redis Library Conflict**
*   **Issue:** `aioredis` (v1.x) conflicts with modern `redis` (v5.x) library, causing `duplicate base class TimeoutError`.
*   **Solution:** Removed `aioredis`. Use `redis.asyncio` (included in `redis>=4.2.0`).

---

## **3. Architecture**

### **Headless Sovereignty**
*   **Finding:** Coupling the core logic to "SillyTavern" creates unnecessary fragility.
*   **Decision:** Move to a pure "Headless" architecture (v4 specs). The Core (Python) is the source of truth; any frontend is just a viewer.
