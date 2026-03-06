# Throne Control Panels Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Upgrade the Bifrost and Tools tabs from read-only viewers to interactive control panels, and consolidate the Ryuzu/Ryuzu Meyer spirit duplication.

**Architecture:** Backend-first — add new API endpoints to `src/api/config.py`, add warm-up logic to `src/core/llm_client.py`, add MCP management methods to `src/mcp/client.py`. Then upgrade Flutter widgets. Each task is independently testable.

**Tech Stack:** Python/FastAPI (backend), Dart/Flutter (frontend), PostgreSQL (Ryuzu migration)

---

### Task 1: Ryuzu Consolidation

**Files:**
- Create: `scripts/merge_ryuzu.py`
- Create: `tests/test_ryuzu_merge.py`

**Step 1: Write the merge script**

```python
"""
One-time script: Merge 'Ryuzu Meyer' into 'Ryuzu'.
Combines personality traits, reassigns all foreign keys, deletes the duplicate.
"""
import asyncio
import logging
from src.core.database import get_database
from sqlalchemy import text

logger = logging.getLogger("sovereign.migrate")

async def merge_ryuzu():
    db = get_database()
    await db.initialize()

    async with db.session() as session:
        # Find both agents
        result = await session.execute(
            text("SELECT id, name, designation, traits FROM agents WHERE name ILIKE :pattern"),
            {"pattern": "%ryuzu%"}
        )
        rows = result.mappings().all()

        if len(rows) < 2:
            logger.info("No duplicate Ryuzu found. Nothing to merge.")
            return

        # Identify canonical (shortest name = 'Ryuzu') and duplicate
        canonical = None
        duplicate = None
        for row in rows:
            if row["name"].strip().lower() == "ryuzu":
                canonical = row
            else:
                duplicate = row

        if not canonical or not duplicate:
            logger.error(f"Could not identify canonical/duplicate from: {[r['name'] for r in rows]}")
            return

        canonical_id = str(canonical["id"])
        duplicate_id = str(duplicate["id"])

        logger.info(f"Merging '{duplicate['name']}' ({duplicate_id}) into '{canonical['name']}' ({canonical_id})")

        # Merge designation if canonical is empty
        if not canonical.get("designation") and duplicate.get("designation"):
            await session.execute(
                text("UPDATE agents SET designation = :designation WHERE id = :id"),
                {"designation": duplicate["designation"], "id": canonical_id}
            )

        # Reassign tether_messages
        for col in ["sender_agent_id", "recipient_agent_id"]:
            await session.execute(
                text(f"UPDATE tether_messages SET {col} = :canonical WHERE {col} = :duplicate"),
                {"canonical": canonical_id, "duplicate": duplicate_id}
            )

        # Reassign tether_participants
        # Delete duplicate's participation if canonical already participates in same thread
        await session.execute(
            text("""
                DELETE FROM tether_participants
                WHERE agent_id = :duplicate
                AND thread_id IN (SELECT thread_id FROM tether_participants WHERE agent_id = :canonical)
            """),
            {"canonical": canonical_id, "duplicate": duplicate_id}
        )
        await session.execute(
            text("UPDATE tether_participants SET agent_id = :canonical WHERE agent_id = :duplicate"),
            {"canonical": canonical_id, "duplicate": duplicate_id}
        )

        # Reassign projects
        await session.execute(
            text("UPDATE projects SET lead_agent_id = :canonical WHERE lead_agent_id = :duplicate"),
            {"canonical": canonical_id, "duplicate": duplicate_id}
        )

        # Delete duplicate
        await session.execute(
            text("DELETE FROM agents WHERE id = :duplicate"),
            {"duplicate": duplicate_id}
        )

        await session.commit()
        logger.info(f"Merge complete. '{duplicate['name']}' removed.")

if __name__ == "__main__":
    logging.basicConfig(level="INFO")
    asyncio.run(merge_ryuzu())
```

**Step 2: Test locally**

Run inside the Docker container or with DB access:
```bash
python scripts/merge_ryuzu.py
```
Expected: "Merge complete" log message. Verify with:
```bash
docker compose exec postgres psql -U voidcat -d voidcat_rdc -c "SELECT id, name FROM agents WHERE name ILIKE '%ryuzu%';"
```
Expected: single row, name = "Ryuzu"

**Step 3: Commit**

```bash
git add scripts/merge_ryuzu.py
git commit -m "fix: merge Ryuzu Meyer duplicate into canonical Ryuzu"
```

---

### Task 2: Backend — Single Provider Health Check + Test Reply

**Files:**
- Modify: `src/api/config.py` (add 2 endpoints)
- Create: `tests/test_config_api.py`

**Step 1: Write failing tests**

```python
"""Tests for config API endpoints."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

# We test the router functions directly since they depend on singletons

@pytest.mark.asyncio
async def test_health_check_single_provider():
    """GET /config/llm/health/{name} returns health for one provider."""
    from src.api.config import get_llm_health_single
    with patch("src.api.config.get_llm_client") as mock_get:
        client = MagicMock()
        client.providers = {"lm_studio": MagicMock(provider_type=MagicMock(value="lm_studio"), model="auto", endpoint="http://localhost:1234/v1")}
        client.health_check = AsyncMock(return_value=True)
        mock_get.return_value = client

        result = await get_llm_health_single("lm_studio")
        assert result["online"] is True
        assert result["name"] == "lm_studio"


@pytest.mark.asyncio
async def test_health_check_unknown_provider():
    """GET /config/llm/health/{name} returns 404 for unknown provider."""
    from src.api.config import get_llm_health_single
    with patch("src.api.config.get_llm_client") as mock_get:
        client = MagicMock()
        client.providers = {}
        mock_get.return_value = client

        with pytest.raises(Exception):  # HTTPException
            await get_llm_health_single("nonexistent")


@pytest.mark.asyncio
async def test_test_reply():
    """POST /config/llm/test/{name} sends test prompt and returns response."""
    from src.api.config import test_llm_provider
    with patch("src.api.config.get_llm_client") as mock_get:
        client = MagicMock()
        client.providers = {"lm_studio": MagicMock()}
        resp = MagicMock()
        resp.content = "Hello! I'm working."
        resp.model = "qwen3-4b"
        resp.provider = "lm_studio"
        resp.tokens_used = 10
        client.complete = AsyncMock(return_value=resp)
        mock_get.return_value = client

        result = await test_llm_provider("lm_studio")
        assert result["success"] is True
        assert "Hello" in result["response"]
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_config_api.py -v
```
Expected: FAIL — `get_llm_health_single` and `test_llm_provider` don't exist yet.

**Step 3: Implement the endpoints**

Add to `src/api/config.py` after the existing `/config/llm/health` endpoint:

```python
@router.get("/llm/health/{provider_name}")
async def get_llm_health_single(provider_name: str) -> Dict[str, Any]:
    """Check health of a single LLM provider."""
    client = get_llm_client()
    if provider_name not in client.providers:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_name}' not found")

    provider = client.providers[provider_name]
    try:
        online = await client.health_check(provider_name)
    except Exception:
        online = False

    return {
        "name": provider_name,
        "online": online,
        "type": provider.provider_type.value,
        "model": provider.model,
        "endpoint": provider.endpoint,
    }


@router.post("/llm/test/{provider_name}")
async def test_llm_provider(provider_name: str) -> Dict[str, Any]:
    """Send a test prompt to a specific provider and return the response."""
    client = get_llm_client()
    if provider_name not in client.providers:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_name}' not found")

    from src.core.llm_client import ChatMessage
    try:
        response = await client.complete(
            messages=[ChatMessage(role="user", content="Say hello in one sentence.")],
            provider_name=provider_name,
            use_fallback=False,
            max_tokens=50,
            temperature=0.7,
        )
        return {
            "success": True,
            "response": response.content,
            "model": response.model,
            "provider": response.provider,
            "tokens_used": response.tokens_used,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "provider": provider_name,
        }
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_config_api.py -v
```
Expected: 3/3 PASS

**Step 5: Commit**

```bash
git add src/api/config.py tests/test_config_api.py
git commit -m "feat: add single-provider health check and test reply endpoints"
```

---

### Task 3: Backend — LM Studio Auto-Warm for AUTO Mode

**Files:**
- Modify: `src/core/llm_client.py` (add `warm_local_provider` method)
- Modify: `src/api/config.py` (add `/config/llm/warm` endpoint)
- Modify: `src/main.py` (call warm on startup when AUTO)

**Step 1: Add warm method to LLMClient**

Add to `LLMClient` class in `src/core/llm_client.py`:

```python
async def warm_local_provider(self) -> Dict[str, Any]:
    """
    Warm up LM Studio by checking if a model is loaded,
    and requesting qwen3-4b-thinking if not.
    Returns status dict for logging/API response.
    """
    lm_config = self.providers.get("lm_studio")
    if not lm_config:
        return {"status": "skipped", "reason": "lm_studio provider not configured"}

    base_url = lm_config.endpoint.replace("/v1", "")
    target_model = os.getenv("LM_STUDIO_WARM_MODEL", "qwen3-4b-thinking")

    try:
        # Check what's loaded
        resp = await self._client.get(f"{lm_config.endpoint}/models", timeout=5.0)
        if resp.status_code == 200:
            models = resp.json().get("data", [])
            loaded_ids = [m.get("id", "") for m in models]
            if any(target_model.lower() in mid.lower() for mid in loaded_ids):
                return {"status": "ready", "model": target_model, "already_loaded": True}

        # Try to load the model via LM Studio API
        # LM Studio supports POST /v1/models/load (non-standard but common)
        load_resp = await self._client.post(
            f"{base_url}/api/v0/models/load",
            json={"model": target_model},
            timeout=30.0,
        )
        if load_resp.status_code == 200:
            return {"status": "ready", "model": target_model, "already_loaded": False}
        else:
            return {"status": "partial", "reason": f"Load request returned {load_resp.status_code}", "model": target_model}

    except Exception as e:
        logger.warning(f"LM Studio warm-up failed: {e}")
        return {"status": "failed", "reason": str(e)}
```

**Step 2: Add warm endpoint to config.py**

```python
@router.post("/llm/warm")
async def warm_local_provider() -> Dict[str, Any]:
    """Trigger LM Studio warm-up (load model for local fallback)."""
    client = get_llm_client()
    result = await client.warm_local_provider()
    return result
```

**Step 3: Add warm call to lifespan in main.py**

After `initialize_llm_from_config()` in the lifespan function:

```python
# Warm up local provider for AUTO mode
from src.core.llm_client import get_llm_client as _get_llm
try:
    _client = _get_llm()
    if _client.inference_mode == "AUTO":
        warm_result = await _client.warm_local_provider()
        logger.info(f"LM Studio warm-up: {warm_result.get('status', 'unknown')}")
except Exception as e:
    logger.warning(f"LM Studio warm-up failed (non-blocking): {e}")
```

**Step 4: Test manually**

```bash
# Rebuild and restart
docker compose build middleware && docker compose up -d middleware
# Check logs for warm-up
docker compose logs middleware | grep -i warm
# Test endpoint
curl -X POST http://localhost:8090/api/config/llm/warm -H "X-API-Key: voidcat-secure-handshake-2026"
```

**Step 5: Commit**

```bash
git add src/core/llm_client.py src/api/config.py src/main.py
git commit -m "feat: add LM Studio auto-warm for AUTO mode on startup"
```

---

### Task 4: Backend — AUTO Mode Cloud-First Routing + Failure Tracking

**Files:**
- Modify: `src/core/llm_client.py` (update AUTO routing logic, add failure state)

**Step 1: Add failure tracking to LLMClient**

Add fields to `LLMClient.__init__`:

```python
self.last_cloud_failure: Optional[str] = None
self.last_cloud_failure_at: Optional[datetime] = None
self.cloud_healthy: bool = True
```

**Step 2: Update AUTO routing in `complete()` method**

Replace the AUTO block in `complete()`:

```python
elif self.inference_mode == "AUTO":
    # Cloud-first, local fallback
    cloud_providers = [
        p for p in self.fallback_chain
        if p in self.providers and self.providers[p].provider_type in [ProviderType.OPENROUTER, ProviderType.OPENAI]
    ]
    local_providers = [
        p for p in self.fallback_chain
        if p in self.providers and self.providers[p].provider_type in [ProviderType.OLLAMA, ProviderType.LM_STUDIO]
    ]
    providers_to_try = cloud_providers + local_providers
```

**Step 3: Add failure tracking after fallback**

In the `for p_name in providers_to_try` loop in `complete()`, after a cloud provider fails:

```python
except Exception as e:
    logger.warning(f"Provider {p_name} failed: {e}")
    last_error = e
    if self.inference_mode == "AUTO":
        ptype = self.providers[p_name].provider_type
        if ptype in [ProviderType.OPENROUTER, ProviderType.OPENAI]:
            self.cloud_healthy = False
            self.last_cloud_failure = str(e)
            self.last_cloud_failure_at = datetime.now(timezone.utc)
            self.current_route = "LOCAL"
        elif ptype in [ProviderType.OLLAMA, ProviderType.LM_STUDIO]:
            self.current_route = "CLOUD"
```

On success, update route and clear failure:

```python
try:
    result = await self._complete_with_provider(...)
    # Track successful route
    ptype = self.providers[p_name].provider_type
    if ptype in [ProviderType.OPENROUTER, ProviderType.OPENAI]:
        self.current_route = "CLOUD"
        if not self.cloud_healthy:
            self.cloud_healthy = True
            logger.info("Cloud provider recovered")
    else:
        self.current_route = "LOCAL"
    return result
```

**Step 4: Expose failure state in inference status endpoint**

Update `get_inference_config()` in `src/api/config.py`:

```python
@router.get("/inference", response_model=None)
async def get_inference_config():
    client = get_llm_client()
    return {
        "mode": client.inference_mode,
        "current_route": client.current_route,
        "cloud_healthy": client.cloud_healthy,
        "last_cloud_failure": client.last_cloud_failure,
        "last_cloud_failure_at": client.last_cloud_failure_at.isoformat() if client.last_cloud_failure_at else None,
    }
```

**Step 5: Test manually**

```bash
docker compose build middleware && docker compose up -d middleware
curl http://localhost:8090/api/config/inference -H "X-API-Key: voidcat-secure-handshake-2026"
```
Expected: JSON with `cloud_healthy`, `last_cloud_failure` fields.

**Step 6: Commit**

```bash
git add src/core/llm_client.py src/api/config.py
git commit -m "feat: AUTO mode cloud-first routing with failure tracking"
```

---

### Task 5: Backend — MCP Tool Management Endpoints

**Files:**
- Modify: `src/mcp/client.py` (add `disconnect_server` method)
- Modify: `src/api/config.py` (add 5 endpoints)
- Create: `tests/test_config_tools_api.py`

**Step 1: Add disconnect method to MCPManager**

Add to `MCPManager` in `src/mcp/client.py`:

```python
async def disconnect_server(self, server_name: str) -> bool:
    """Disconnect a specific MCP server and remove its tools."""
    if server_name not in self.sessions:
        return False

    # Remove tools from this server
    self.available_tools = [t for t in self.available_tools if t.get("server") != server_name]

    # Close session (best-effort)
    try:
        del self.sessions[server_name]
    except Exception as e:
        logger.warning(f"Error disconnecting {server_name}: {e}")

    logger.info(f"Disconnected MCP server: {server_name}")
    return True
```

**Step 2: Add tool management endpoints to config.py**

```python
@router.post("/tools/connect/{server_name}")
async def connect_mcp_server(server_name: str) -> Dict[str, Any]:
    """Connect or reconnect an MCP server."""
    mcp = get_mcp_manager()

    # Disconnect first if already connected
    if server_name in mcp.sessions:
        await mcp.disconnect_server(server_name)

    try:
        await mcp.connect_server(server_name)
        tool_count = len([t for t in mcp.available_tools if t.get("server") == server_name])
        return {"status": "connected", "server": server_name, "tools_loaded": tool_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect: {str(e)}")


@router.post("/tools/disconnect/{server_name}")
async def disconnect_mcp_server(server_name: str) -> Dict[str, Any]:
    """Disconnect an MCP server."""
    mcp = get_mcp_manager()
    if server_name not in mcp.sessions:
        raise HTTPException(status_code=404, detail=f"Server '{server_name}' not connected")

    await mcp.disconnect_server(server_name)
    return {"status": "disconnected", "server": server_name}


@router.post("/tools/test/{server_name}/{tool_name}")
async def test_mcp_tool(server_name: str, tool_name: str, request: Request) -> Dict[str, Any]:
    """Execute an MCP tool with provided arguments and return the result."""
    mcp = get_mcp_manager()
    if server_name not in mcp.sessions:
        raise HTTPException(status_code=404, detail=f"Server '{server_name}' not connected")

    # Validate tool exists
    tool_exists = any(
        t["name"] == tool_name and t["server"] == server_name
        for t in mcp.available_tools
    )
    if not tool_exists:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found on '{server_name}'")

    try:
        body = await request.json()
    except Exception:
        body = {}

    result = await mcp.execute_tool(server_name, tool_name, body)
    return {"tool": tool_name, "server": server_name, "result": result}


@router.get("/tools/registry")
async def get_mcp_registry() -> Dict[str, Any]:
    """Return the raw MCP server registry (available server definitions)."""
    from src.mcp.config import MCP_SERVER_REGISTRY
    mcp = get_mcp_manager()

    registry = {}
    for name, config in MCP_SERVER_REGISTRY.items():
        registry[name] = {
            "command": config["command"],
            "args": config["args"],
            "connected": name in mcp.sessions,
        }
    return {"servers": registry}


@router.post("/tools/registry")
async def add_mcp_server_to_registry(request: Request) -> Dict[str, Any]:
    """Add or update a server in the MCP registry (runtime only)."""
    from src.mcp.config import MCP_SERVER_REGISTRY

    body = await request.json()
    name = body.get("name")
    command = body.get("command")
    args = body.get("args", [])

    if not name or not command:
        raise HTTPException(status_code=400, detail="'name' and 'command' are required")

    MCP_SERVER_REGISTRY[name] = {
        "command": command,
        "args": args if isinstance(args, list) else args.split(),
        "env": {"PATH": os.environ.get("PATH", "")},
    }
    return {"status": "added", "server": name}
```

**Step 3: Run tests**

```bash
pytest tests/test_config_tools_api.py -v
```

**Step 4: Commit**

```bash
git add src/mcp/client.py src/api/config.py tests/test_config_tools_api.py
git commit -m "feat: add MCP tool connect/disconnect/test/registry endpoints"
```

---

### Task 6: Frontend — Bifrost Panel Upgrade

**Files:**
- Modify: `voidcat_tether/lib/features/dashboard/widgets/bifrost_panel.dart`
- Modify: `voidcat_tether/lib/services/api_service.dart` (add new API calls)

**Step 1: Add API methods to ApiService**

Add to `api_service.dart`:

```dart
/// Test a single LLM provider's health.
Future<Map<String, dynamic>> testProviderHealth(String name) async {
  final res = await _client.get(
    Uri.parse('$_base/api/config/llm/health/$name'),
    headers: _headers,
  );
  return jsonDecode(res.body) as Map<String, dynamic>;
}

/// Send a test prompt to a provider and get response.
Future<Map<String, dynamic>> testProviderReply(String name) async {
  final res = await _client.post(
    Uri.parse('$_base/api/config/llm/test/$name'),
    headers: _headers,
  );
  return jsonDecode(res.body) as Map<String, dynamic>;
}

/// Save full LLM config.
Future<Map<String, dynamic>> saveLLMConfig(Map<String, dynamic> config) async {
  final res = await _client.post(
    Uri.parse('$_base/api/config/llm'),
    headers: _headers,
    body: jsonEncode(config),
  );
  return jsonDecode(res.body) as Map<String, dynamic>;
}

/// Warm up local provider.
Future<Map<String, dynamic>> warmLocalProvider() async {
  final res = await _client.post(
    Uri.parse('$_base/api/config/llm/warm'),
    headers: _headers,
  );
  return jsonDecode(res.body) as Map<String, dynamic>;
}
```

**Step 2: Rewrite BifrostPanel**

Full replacement of `bifrost_panel.dart`. Key changes:
- Provider cards expand on tap to show editable fields (endpoint, model, API key, max tokens, temp, timeout)
- Dropdowns for provider type and model
- "Test Connection" and "Test Reply" buttons per card with inline result display
- Failure banner at top when `cloud_healthy == false`
- Fallback chain shown as reorderable list
- Save button persists changes

The widget tree should be:
```
Column
├── _failureBanner()          // amber, conditional on !cloud_healthy
├── _header()                 // existing
├── Divider
└── Expanded(ListView)
    ├── _routeVisualization()  // existing
    ├── _modeSwitcher()        // existing LOCAL/AUTO/CLOUD
    ├── _fallbackChain()       // NEW: ReorderableListView of providers
    └── ..._providers.entries.map(_providerCard)  // UPGRADED: expandable
```

Each `_providerCard` when expanded:
```
Container
├── Row [icon, name, model, health dot, expand arrow]  // existing header
└── if expanded:
    ├── DropdownButton(providerType)
    ├── TextField(endpoint)
    ├── TextField(model)
    ├── TextField(apiKey, obscured with reveal)
    ├── Row [TextField(maxTokens), TextField(temperature), TextField(timeout)]
    ├── Row [TestConnection btn, TestReply btn]
    ├── if testResult: Text(result)
    └── SaveButton
```

**Step 3: Build and verify**

```bash
cd voidcat_tether && flutter build web --release
# Copy output to src/static/
cp -r build/web/* ../src/static/
```

**Step 4: Commit**

```bash
git add voidcat_tether/lib/ src/static/
git commit -m "feat: interactive Bifrost panel with provider editing and testing"
```

---

### Task 7: Frontend — Tools Panel Upgrade

**Files:**
- Modify: `voidcat_tether/lib/features/dashboard/widgets/tools_panel.dart`
- Modify: `voidcat_tether/lib/services/api_service.dart`

**Step 1: Add API methods to ApiService**

```dart
/// Connect/reconnect an MCP server.
Future<Map<String, dynamic>> connectMCPServer(String name) async {
  final res = await _client.post(
    Uri.parse('$_base/api/config/tools/connect/$name'),
    headers: _headers,
  );
  return jsonDecode(res.body) as Map<String, dynamic>;
}

/// Disconnect an MCP server.
Future<Map<String, dynamic>> disconnectMCPServer(String name) async {
  final res = await _client.post(
    Uri.parse('$_base/api/config/tools/disconnect/$name'),
    headers: _headers,
  );
  return jsonDecode(res.body) as Map<String, dynamic>;
}

/// Test an MCP tool with arguments.
Future<Map<String, dynamic>> testMCPTool(String server, String tool, Map<String, dynamic> args) async {
  final res = await _client.post(
    Uri.parse('$_base/api/config/tools/test/$server/$tool'),
    headers: _headers,
    body: jsonEncode(args),
  );
  return jsonDecode(res.body) as Map<String, dynamic>;
}

/// Get MCP server registry.
Future<Map<String, dynamic>> getMCPRegistry() async {
  final res = await _client.get(
    Uri.parse('$_base/api/config/tools/registry'),
    headers: _headers,
  );
  return jsonDecode(res.body) as Map<String, dynamic>;
}

/// Add server to MCP registry.
Future<Map<String, dynamic>> addMCPServer(String name, String command, List<String> args) async {
  final res = await _client.post(
    Uri.parse('$_base/api/config/tools/registry'),
    headers: _headers,
    body: jsonEncode({'name': name, 'command': command, 'args': args}),
  );
  return jsonDecode(res.body) as Map<String, dynamic>;
}
```

**Step 2: Upgrade ToolsPanel**

Key changes:
- "Add MCP Server" button at top → opens inline form with dropdown (known types) or custom fields
- Each server group gets "Test" (reconnect) and "Disconnect" buttons in the header
- Each tool tile gets a play icon → shows auto-generated form from JSON schema → Run button → inline result
- Results shown in a monospace container below the form

Widget tree:
```
Column
├── _header()          // existing + add button
├── Divider
├── if _showAddForm: _addServerForm()  // NEW
└── Expanded(ListView)
    └── _servers.entries.map(_serverGroup)  // UPGRADED
        ├── ExpansionTile header [dot, name, count, Test btn, Disconnect btn]
        └── tools.map(_toolTile)
            ├── Row [name, play icon]
            ├── if expanded: _toolTestForm(schema)
            └── if result: _toolResultView(result)
```

**Step 3: Build and verify**

```bash
cd voidcat_tether && flutter build web --release
cp -r build/web/* ../src/static/
```

**Step 4: Commit**

```bash
git add voidcat_tether/lib/ src/static/
git commit -m "feat: interactive Tools panel with add/remove/test MCP tools"
```

---

### Task 8: Agent Activity Feed (Agent Grid Enhancement)

**Files:**
- Modify: `voidcat_tether/lib/features/dashboard/widgets/agent_grid.dart`
- Modify: `voidcat_tether/lib/services/api_service.dart`
- Modify: `src/api/config.py` (add agent activity endpoint)

**Step 1: Add backend endpoint for agent recent activity**

Add to `src/api/config.py`:

```python
@router.get("/agents/{agent_id}/activity")
async def get_agent_activity(agent_id: str, limit: int = 10) -> Dict[str, Any]:
    """
    Return recent heartbeat decisions and actions for an agent.
    Pulls from the system_logs/thought_log table.
    """
    db = get_database()
    async with db.session() as session:
        result = await session.execute(
            text("""
                SELECT action, details, timestamp
                FROM thought_log
                WHERE agent_id = :agent_id
                ORDER BY timestamp DESC
                LIMIT :limit
            """),
            {"agent_id": agent_id, "limit": limit}
        )
        rows = result.mappings().all()

    return {
        "agent_id": agent_id,
        "activity": [
            {
                "action": row["action"],
                "details": row.get("details", ""),
                "timestamp": row["timestamp"].isoformat() if row.get("timestamp") else None,
            }
            for row in rows
        ],
    }
```

**Step 2: Add API method to ApiService (Dart)**

```dart
/// Get recent activity (heartbeat decisions) for an agent.
Future<Map<String, dynamic>> getAgentActivity(String agentId, {int limit = 10}) async {
  final res = await _client.get(
    Uri.parse('$_base/api/config/agents/$agentId/activity?limit=$limit'),
    headers: _headers,
  );
  return jsonDecode(res.body) as Map<String, dynamic>;
}
```

**Step 3: Add activity section to agent_grid.dart**

When an agent is selected, show a collapsible activity feed below the agent card. Shows last 5-8 MUSE decisions with timestamps:

```
┌─────────────────────────┐
│ ● Echo                  │  ← selected agent card
│   The Void Vessel       │
│                  focused │
├─────────────────────────┤
│ RECENT ACTIVITY         │  ← new section
│ 00:14  MUSE → ACT       │
│ 00:12  ACT: RESPOND     │
│ 00:10  MUSE → SLEEP     │
│ 00:08  MUSE → PONDER    │
│ 00:06  PONDER: REFLECT  │
└─────────────────────────┘
```

Each entry: timestamp (HH:MM), action, details. Color-coded: ACT=green, PONDER=blue, SLEEP=gray. Auto-refreshes every 30s. Does NOT appear in the thread panel or comms — stays in the agent sidebar only.

**Step 4: Build and verify**

```bash
cd voidcat_tether && flutter build web --release
cp -r build/web/* ../src/static/
```

**Step 5: Commit**

```bash
git add voidcat_tether/lib/ src/static/ src/api/config.py
git commit -m "feat: agent activity feed showing recent heartbeat decisions"
```

---

### Task 9: Version Bump

**Files:**
- Modify: `src/main.py` (version string in FastAPI app)

**Step 1: Update version**

In `src/main.py`, update the FastAPI app version:

```python
app = FastAPI(
    title="Sovereign Spirit",
    version="1.2.0",  # was 1.1.0 or 1.0.0
    ...
)
```

**Step 2: Commit**

```bash
git add src/main.py
git commit -m "chore: bump version to 1.2.0 — Throne control panels release"
```

---

### Task 10: Integration Test + Final Verification

**Files:**
- Modify: `tests/test_agent_api.py` or create `tests/test_throne_integration.py`

**Step 1: Verify all new endpoints respond**

```bash
# Health check single provider
curl http://localhost:8090/api/config/llm/health/lm_studio -H "X-API-Key: voidcat-secure-handshake-2026"

# Test reply
curl -X POST http://localhost:8090/api/config/llm/test/lm_studio -H "X-API-Key: voidcat-secure-handshake-2026"

# Warm
curl -X POST http://localhost:8090/api/config/llm/warm -H "X-API-Key: voidcat-secure-handshake-2026"

# Inference status (should show cloud_healthy field)
curl http://localhost:8090/api/config/inference -H "X-API-Key: voidcat-secure-handshake-2026"

# MCP registry
curl http://localhost:8090/api/config/tools/registry -H "X-API-Key: voidcat-secure-handshake-2026"

# MCP reconnect
curl -X POST http://localhost:8090/api/config/tools/connect/filesystem -H "X-API-Key: voidcat-secure-handshake-2026"

# MCP disconnect
curl -X POST http://localhost:8090/api/config/tools/disconnect/filesystem -H "X-API-Key: voidcat-secure-handshake-2026"

# Ryuzu check
docker compose exec postgres psql -U voidcat -d voidcat_rdc -c "SELECT id, name FROM agents WHERE name ILIKE '%ryuzu%';"
```

**Step 2: Load Throne in browser**

Open `http://localhost:8090/` and verify:
- Agent grid shows single Ryuzu (no Meyer)
- Bifrost tab: mode switcher works, provider cards expand, test buttons work
- Tools tab: server groups show test/disconnect, add server form works

**Step 3: Final commit**

```bash
git add -A
git commit -m "feat: Throne control panels — Bifrost editing, Tools management, Ryuzu merge"
```

---

## Task Dependency Graph

```
Task 1 (Ryuzu) ──────────────────────────────────────────────┐
Task 2 (Health/Test endpoints) ──┬── Task 6 (Bifrost UI) ────┤
Task 3 (LM Studio warm) ────────┤                            ├── Task 9 (Version) ── Task 10 (Integration)
Task 4 (AUTO routing) ──────────┘                            │
Task 5 (MCP endpoints) ──────────── Task 7 (Tools UI) ──────┤
                                    Task 8 (Activity Feed) ──┘
```

Tasks 1-5 are independent (all backend). Tasks 6-8 depend on their backend tasks. Task 9-10 depend on everything.
