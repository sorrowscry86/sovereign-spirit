# MCP Wiring + Project System + Town Sim Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Wire MCP tool calls into the agent heartbeat, add a persistent Project/Goal system, and give idle agents a Town Sim PONDER mode with self-directed memory retrieval.

**Architecture:** Single-shot tool call per ACT cycle (Option A). MCPManager initializes at startup connecting `filesystem` and `search` servers. `CompletionResponse` gains a `tool_calls` field; the HTTP path passes tools to the model and parses the response. `process_pending_task()` is rewritten to use this flow. Projects live in Postgres with Neo4j tasks extended to carry `project_id` and `assigned_agent_id`. PONDER is a third MUSE state triggered probabilistically on idle cycles; it runs a Prism self-recall before sending a separate prompt.

**Tech Stack:** FastAPI, SQLAlchemy asyncpg, Neo4j async driver, Weaviate, Redis, httpx, MCP Python SDK (`mcp`), Pydantic v2, pytest

---

## Task 1: LLMClient — tool call support

**Files:**
- Modify: `src/core/llm_client.py`
- Test: `tests/test_llm_tool_calls.py`

### Step 1: Write the failing test

```python
# tests/test_llm_tool_calls.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.core.llm_client import LLMClient, ChatMessage, CompletionResponse

FAKE_TOOL = [{
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "Read a file",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}}}
    }
}]

FAKE_TOOL_RESPONSE = {
    "choices": [{
        "message": {
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": "call_abc",
                "type": "function",
                "function": {"name": "read_file", "arguments": '{"path": "/app/test.txt"}'}
            }]
        },
        "finish_reason": "tool_calls"
    }],
    "model": "test-model",
    "usage": {"total_tokens": 50}
}

@pytest.mark.asyncio
async def test_complete_returns_tool_calls():
    client = LLMClient()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = FAKE_TOOL_RESPONSE
    mock_response.raise_for_status = MagicMock()

    with patch.object(client._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        result = await client.complete(
            messages=[ChatMessage(role="user", content="read the file")],
            tools=FAKE_TOOL,
            provider_name="lm_studio",
        )

    assert result.tool_calls != []
    assert result.tool_calls[0]["function"]["name"] == "read_file"
    assert result.finish_reason == "tool_calls"

@pytest.mark.asyncio
async def test_complete_without_tools_unchanged():
    """Existing call sites still work with no tools argument."""
    client = LLMClient()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "hello", "tool_calls": []}, "finish_reason": "stop"}],
        "model": "test-model", "usage": {"total_tokens": 10}
    }
    mock_response.raise_for_status = MagicMock()

    with patch.object(client._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        result = await client.complete(
            messages=[ChatMessage(role="user", content="hi")],
            provider_name="lm_studio",
        )

    assert result.tool_calls == []
    assert result.content == "hello"
```

### Step 2: Run test to verify it fails

```bash
cd "C:/Users/Wykeve/Projects/The Great Library/05_Projects/01_Active/Sovereign Spirit"
pytest tests/test_llm_tool_calls.py -v
```

Expected: `FAILED` — `CompletionResponse` has no `tool_calls` field, `complete()` has no `tools` param.

### Step 3: Implement

In `src/core/llm_client.py`:

**3a.** Add `tool_calls` to `CompletionResponse` (after `finish_reason`):
```python
tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
```

**3b.** Add `tools` param to `complete()` signature (after `complexity`):
```python
tools: Optional[List[Dict[str, Any]]] = None,
```

Pass it through to `_complete_with_provider()`:
```python
return await self._complete_with_provider(
    p_name, messages, max_tokens, temperature, complexity, tools
)
```

**3c.** Add `tools` param to `_complete_with_provider()` signature (after `complexity`):
```python
tools: Optional[List[Dict[str, Any]]] = None,
```

**3d.** In the LM Studio SDK block, add at the top of the `if config.provider_type == ProviderType.LM_STUDIO:` branch — skip SDK if tools are requested (SDK doesn't support function calling reliably):
```python
if tools:
    # Force HTTP path for tool calls — SDK doesn't support function calling
    pass  # fall through to HTTP implementation below
else:
    # existing SDK block ...
```
Wrap the existing SDK try/except inside the `else:` block.

**3e.** In the HTTP payload dict, add tools if provided:
```python
payload = {
    "model": config.model,
    "messages": [m.model_dump() for m in messages],
    "max_tokens": max_tokens or config.max_tokens,
    "temperature": temperature if temperature is not None else config.temperature,
    "stream": False,
}
if tools:
    payload["tools"] = tools
```

**3f.** In the HTTP response parsing, extract `tool_calls`:
```python
choice = data["choices"][0]
message = choice["message"]
content = message.get("content") or ""
raw_tool_calls = message.get("tool_calls") or []

return CompletionResponse(
    content=content,
    model=data.get("model", config.model),
    provider=provider_name,
    tokens_used=data.get("usage", {}).get("total_tokens"),
    finish_reason=choice.get("finish_reason"),
    tool_calls=raw_tool_calls,
)
```

### Step 4: Run test to verify it passes

```bash
pytest tests/test_llm_tool_calls.py -v
```

Expected: `2 passed`

### Step 5: Commit

```bash
git add src/core/llm_client.py tests/test_llm_tool_calls.py
git commit -m "feat: add tool_calls support to LLMClient complete()"
```

---

## Task 2: MCPManager singleton + startup init

**Files:**
- Modify: `src/mcp/client.py`
- Modify: `src/main.py`
- Test: `tests/test_mcp_singleton.py`

### Step 1: Write the failing test

```python
# tests/test_mcp_singleton.py
from src.mcp.client import get_mcp_manager, MCPManager

def test_get_mcp_manager_returns_singleton():
    a = get_mcp_manager()
    b = get_mcp_manager()
    assert a is b
    assert isinstance(a, MCPManager)

def test_get_tools_for_llm_empty_when_no_servers():
    mgr = get_mcp_manager()
    tools = mgr.get_tools_for_llm()
    assert isinstance(tools, list)
```

### Step 2: Run test to verify it fails

```bash
pytest tests/test_mcp_singleton.py -v
```

Expected: `FAILED` — `get_mcp_manager` and `get_tools_for_llm` don't exist.

### Step 3: Implement

**3a.** Add `get_tools_for_llm()` method to `MCPManager` class in `src/mcp/client.py`:

```python
def get_tools_for_llm(self) -> list[dict]:
    """Return available tools in OpenAI function-call format."""
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["schema"],
            },
        }
        for t in self.available_tools
    ]
```

**3b.** Add singleton at the bottom of `src/mcp/client.py` (after the class, before EOF):

```python
_mcp_manager: Optional["MCPManager"] = None


def get_mcp_manager() -> "MCPManager":
    """Get or create the singleton MCPManager."""
    global _mcp_manager
    if _mcp_manager is None:
        _mcp_manager = MCPManager()
    return _mcp_manager


async def shutdown_mcp_manager() -> None:
    """Gracefully close all MCP server connections."""
    global _mcp_manager
    if _mcp_manager is not None:
        await _mcp_manager.shutdown()
        _mcp_manager = None
```

**3c.** Wire into `src/main.py` lifespan. Add import at top of file:
```python
from src.mcp.client import get_mcp_manager, shutdown_mcp_manager
```

Add MCP startup block in `lifespan()` after the heartbeat start block:
```python
# Initialize MCP tool servers
mcp = get_mcp_manager()
try:
    await mcp.connect_server("filesystem")
    logger.info(f"MCP filesystem server connected ({len(mcp.available_tools)} tools)")
except Exception as e:
    logger.warning(f"MCP filesystem server failed to connect: {e}")

if os.getenv("BRAVE_SEARCH_API_KEY"):
    try:
        await mcp.connect_server("search")
        logger.info(f"MCP search server connected ({len(mcp.available_tools)} tools total)")
    except Exception as e:
        logger.warning(f"MCP search server failed to connect: {e}")
else:
    logger.info("MCP search server skipped (BRAVE_SEARCH_API_KEY not set)")
```

Add MCP shutdown in the shutdown section (after heartbeat stop):
```python
try:
    await shutdown_mcp_manager()
    logger.info("MCP servers disconnected")
except Exception as e:
    logger.warning(f"MCP shutdown warning: {e}")
```

### Step 4: Run test to verify it passes

```bash
pytest tests/test_mcp_singleton.py -v
```

Expected: `2 passed`

### Step 5: Rebuild and verify startup logs

```bash
docker compose build middleware && docker compose up -d middleware
docker compose logs middleware --tail=30
```

Expected to see: `MCP filesystem server connected (N tools)`

### Step 6: Commit

```bash
git add src/mcp/client.py src/main.py tests/test_mcp_singleton.py
git commit -m "feat: add MCPManager singleton and wire into lifespan startup"
```

---

## Task 3: Rewrite process_pending_task() with tool-use ACT

**Files:**
- Modify: `src/core/heartbeat/pulse.py`
- Test: `tests/test_pulse_tool_act.py`

### Step 1: Write the failing test

```python
# tests/test_pulse_tool_act.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.core.heartbeat.pulse import process_pending_task
from src.core.llm_client import CompletionResponse

TASK = {"task_id": "t-001", "description": "Find information about Neo4j indexes"}

@pytest.mark.asyncio
async def test_act_with_tool_call():
    """ACT: agent calls a tool, result fed back, synthesis stored."""
    db = AsyncMock()
    graph = AsyncMock()
    graph.complete_task = AsyncMock(return_value=True)
    db.queue_response = AsyncMock()

    tool_response = CompletionResponse(
        content="",
        model="test",
        provider="lm_studio",
        tool_calls=[{
            "id": "call_1",
            "type": "function",
            "function": {"name": "read_file", "arguments": '{"path": "/app/README.md"}'}
        }],
        finish_reason="tool_calls",
    )
    synthesis_response = CompletionResponse(
        content="I found that Neo4j uses B-tree indexes.",
        model="test",
        provider="lm_studio",
        tool_calls=[],
        finish_reason="stop",
    )

    with patch("src.core.heartbeat.pulse.get_llm_client") as mock_client_fn, \
         patch("src.core.heartbeat.pulse.get_mcp_manager") as mock_mcp_fn:

        mock_client = AsyncMock()
        mock_client.complete = AsyncMock(side_effect=[tool_response, synthesis_response])
        mock_client_fn.return_value = mock_client

        mock_mcp = MagicMock()
        mock_mcp.get_tools_for_llm.return_value = [{"type": "function", "function": {"name": "read_file"}}]
        mock_mcp.execute_tool = AsyncMock(return_value="# README content here")
        mock_mcp_fn.return_value = mock_mcp

        result = await process_pending_task("echo", TASK, db, graph)

    assert result is True
    # Synthesis queued as response
    db.queue_response.assert_called_once()
    queued_content = db.queue_response.call_args[0][0].content
    assert "Neo4j" in queued_content

@pytest.mark.asyncio
async def test_act_without_tool_call():
    """ACT: agent responds directly without calling a tool."""
    db = AsyncMock()
    graph = AsyncMock()
    graph.complete_task = AsyncMock(return_value=True)
    db.queue_response = AsyncMock()

    direct_response = CompletionResponse(
        content="The task is complete. I have reviewed the configuration.",
        model="test",
        provider="lm_studio",
        tool_calls=[],
        finish_reason="stop",
    )

    with patch("src.core.heartbeat.pulse.get_llm_client") as mock_client_fn, \
         patch("src.core.heartbeat.pulse.get_mcp_manager") as mock_mcp_fn:

        mock_client = AsyncMock()
        mock_client.complete = AsyncMock(return_value=direct_response)
        mock_client_fn.return_value = mock_client

        mock_mcp = MagicMock()
        mock_mcp.get_tools_for_llm.return_value = []
        mock_mcp_fn.return_value = mock_mcp

        result = await process_pending_task("echo", TASK, db, graph)

    assert result is True
    # complete() called only once (no tool loop)
    assert mock_client.complete.call_count == 1
```

### Step 2: Run test to verify it fails

```bash
pytest tests/test_pulse_tool_act.py -v
```

Expected: `FAILED` — `process_pending_task` doesn't import `get_mcp_manager` and doesn't use tools.

### Step 3: Add prompt template and imports

In `src/core/heartbeat/pulse.py`, add this import at the top:
```python
from src.mcp.client import get_mcp_manager
```

Add this prompt template after `TASK_COMPLETION_PROMPT`:
```python
TASK_EXECUTION_PROMPT = """[SYSTEM]: You are {agent_name}, {designation}.

Current task: {task_description}

Project context:
{project_context}

You have tools available. Choose the single most useful action to take right now.
If you can answer or complete the task directly without a tool, do so.
Respond with a tool call OR a direct completion — not both."""
```

### Step 4: Rewrite process_pending_task()

Replace the entire `process_pending_task()` function with:

```python
async def process_pending_task(
    agent_id: str,
    task: dict,
    db: DatabaseClient,
    graph: GraphClient,
) -> bool:
    """
    Process a single pending task using LLM + MCP tool loop (Option A).

    Flow:
    1. Build execution prompt with task context
    2. Call LLM with available MCP tools
    3. If tool_call returned: execute tool, synthesize result
    4. If direct response: use as-is
    5. Store result, queue response, mark task complete
    """
    task_id = task.get("task_id", "")
    description = task.get("description", "unknown task")
    project_context = task.get("project_context", "No active project.")

    agent = await db.get_agent_state(agent_id)
    agent_name = agent.name if agent else agent_id
    designation = agent.designation if agent else "Agent"

    logger.info(f"Agent {agent_id} executing task: {task_id} — {description[:60]}")

    client = get_llm_client()
    mcp = get_mcp_manager()
    tools = mcp.get_tools_for_llm()

    prompt = TASK_EXECUTION_PROMPT.format(
        agent_name=agent_name,
        designation=designation,
        task_description=description,
        project_context=project_context,
    )

    messages = [
        ChatMessage(role="system", content=prompt),
        ChatMessage(role="user", content="Execute the task."),
    ]

    try:
        response = await client.complete(
            messages=messages,
            max_tokens=600,
            temperature=0.4,
            use_fallback=True,
            complexity="reasoning",
            tools=tools if tools else None,
        )

        result_text = response.content

        # Tool call branch — execute and synthesize
        if response.tool_calls:
            tool_call = response.tool_calls[0]
            fn = tool_call.get("function", {})
            server_name, tool_name = _resolve_tool_server(fn.get("name", ""), mcp)
            arguments = {}
            try:
                import json as _json
                arguments = _json.loads(fn.get("arguments", "{}"))
            except Exception:
                pass

            logger.info(f"Agent {agent_id} calling tool: {tool_name} on {server_name}")
            tool_result = await mcp.execute_tool(server_name, tool_name, arguments)

            # Synthesis call — no tools, just interpret the result
            synthesis_messages = messages + [
                ChatMessage(role="assistant", content=""),
                ChatMessage(role="user", content=f"Tool result:\n{tool_result}\n\nSummarize what you found and what it means for the task."),
            ]
            synthesis = await client.complete(
                messages=synthesis_messages,
                max_tokens=300,
                temperature=0.4,
                use_fallback=True,
                complexity="reasoning",
            )
            result_text = synthesis.content

        # Mark complete and queue
        await graph.complete_task(task_id)
        queued = QueuedResponse(agent_id=agent_id, content=result_text)
        await db.queue_response(queued)
        logger.info(f"Task {task_id} complete. Result queued.")
        return True

    except Exception as e:
        logger.error(f"Task execution failed for {task_id}: {e}")
        return False


def _resolve_tool_server(tool_name: str, mcp) -> tuple[str, str]:
    """Find which server owns a tool by name."""
    for tool in mcp.available_tools:
        if tool["name"] == tool_name:
            return tool["server"], tool_name
    return "filesystem", tool_name  # Safe fallback
```

### Step 5: Run test to verify it passes

```bash
pytest tests/test_pulse_tool_act.py -v
```

Expected: `2 passed`

### Step 6: Run full test suite to check regressions

```bash
pytest tests/ -v --ignore=tests/verify_chronos_connection.py --ignore=tests/verify_chronos_adapter.py -x
```

Expected: existing tests still pass.

### Step 7: Commit

```bash
git add src/core/heartbeat/pulse.py tests/test_pulse_tool_act.py
git commit -m "feat: rewrite process_pending_task() with MCP single-shot tool call"
```

---

## Task 4: Projects — Postgres schema + DatabaseClient methods

**Files:**
- Create: `src/core/migrations/002_projects.sql`
- Modify: `src/core/database.py`
- Modify: `src/core/graph.py`
- Test: `tests/test_projects_db.py`

### Step 1: Create migration file

```sql
-- src/core/migrations/002_projects.sql
CREATE TABLE IF NOT EXISTS projects (
    project_id   TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    title        TEXT NOT NULL,
    description  TEXT NOT NULL,
    lead_agent_id TEXT REFERENCES agents(agent_id) ON DELETE SET NULL,
    status       TEXT NOT NULL DEFAULT 'active',
    created_at   TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at   TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    progress_notes TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS projects_status_idx ON projects(status);
CREATE INDEX IF NOT EXISTS projects_agent_idx ON projects(lead_agent_id);
```

### Step 2: Write the failing test

```python
# tests/test_projects_db.py
import pytest
from src.core.database import get_database

@pytest.mark.asyncio
async def test_create_and_get_project():
    db = get_database()
    project_id = await db.create_project(
        title="Test Project",
        description="A test project for the build",
        lead_agent_id="echo",
    )
    assert project_id != ""

    project = await db.get_project(project_id)
    assert project["title"] == "Test Project"
    assert project["status"] == "active"
    assert project["progress_notes"] == ""

@pytest.mark.asyncio
async def test_list_projects():
    db = get_database()
    projects = await db.list_projects(status="active")
    assert isinstance(projects, list)

@pytest.mark.asyncio
async def test_append_project_progress():
    db = get_database()
    project_id = await db.create_project(
        title="Progress Test",
        description="Testing progress notes",
        lead_agent_id="echo",
    )
    await db.append_project_progress(project_id, "Completed step 1.")
    project = await db.get_project(project_id)
    assert "Completed step 1." in project["progress_notes"]

@pytest.mark.asyncio
async def test_update_project_status():
    db = get_database()
    project_id = await db.create_project(
        title="Status Test",
        description="Testing status update",
        lead_agent_id="echo",
    )
    await db.update_project_status(project_id, "paused")
    project = await db.get_project(project_id)
    assert project["status"] == "paused"
```

### Step 3: Run test to verify it fails

```bash
pytest tests/test_projects_db.py -v
```

Expected: `FAILED` — methods don't exist yet.

### Step 4: Add Pydantic model and DatabaseClient methods

**4a.** Add `ProjectRecord` model to `src/core/database.py` after `QueuedResponse`:

```python
class ProjectRecord(BaseModel):
    """Represents a long-running project assigned to an agent."""
    project_id: str = ""
    title: str
    description: str
    lead_agent_id: Optional[str] = None
    status: str = "active"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    progress_notes: str = ""
```

**4b.** Add these methods to `DatabaseClient` (before the final closing of the class):

```python
async def create_project(
    self,
    title: str,
    description: str,
    lead_agent_id: Optional[str] = None,
) -> str:
    """Create a new project and return its project_id."""
    async with self.session() as session:
        result = await session.execute(
            text("""
                INSERT INTO projects (title, description, lead_agent_id)
                VALUES (:title, :description, :lead_agent_id)
                RETURNING project_id
            """),
            {"title": title, "description": description, "lead_agent_id": lead_agent_id},
        )
        await session.commit()
        row = result.mappings().first()
        return row["project_id"] if row else ""

async def get_project(self, project_id: str) -> Optional[dict]:
    """Get a project by ID."""
    async with self.session() as session:
        result = await session.execute(
            text("SELECT * FROM projects WHERE project_id = :project_id"),
            {"project_id": project_id},
        )
        row = result.mappings().first()
        return dict(row) if row else None

async def list_projects(self, status: Optional[str] = None) -> list[dict]:
    """List projects, optionally filtered by status."""
    async with self.session() as session:
        if status:
            result = await session.execute(
                text("SELECT * FROM projects WHERE status = :status ORDER BY created_at DESC"),
                {"status": status},
            )
        else:
            result = await session.execute(
                text("SELECT * FROM projects ORDER BY created_at DESC")
            )
        return [dict(row) for row in result.mappings().all()]

async def update_project_status(self, project_id: str, status: str) -> bool:
    """Update project status."""
    async with self.session() as session:
        result = await session.execute(
            text("""
                UPDATE projects
                SET status = :status, updated_at = NOW()
                WHERE project_id = :project_id
            """),
            {"project_id": project_id, "status": status},
        )
        await session.commit()
        return result.rowcount > 0

async def append_project_progress(self, project_id: str, note: str) -> None:
    """Append a timestamped line to the project's progress notes."""
    from datetime import datetime, timezone
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"[{timestamp}] {note}\n"
    async with self.session() as session:
        await session.execute(
            text("""
                UPDATE projects
                SET progress_notes = progress_notes || :line,
                    updated_at = NOW()
                WHERE project_id = :project_id
            """),
            {"project_id": project_id, "line": line},
        )
        await session.commit()

async def get_active_project_for_agent(self, agent_id: str) -> Optional[dict]:
    """Get the most recent active project assigned to an agent."""
    async with self.session() as session:
        result = await session.execute(
            text("""
                SELECT * FROM projects
                WHERE lead_agent_id = :agent_id AND status = 'active'
                ORDER BY updated_at DESC
                LIMIT 1
            """),
            {"agent_id": agent_id},
        )
        row = result.mappings().first()
        return dict(row) if row else None
```

**4c.** Apply the migration. Run inside the container:

```bash
docker compose exec sovereign_state psql -U voidcat -d voidcat_rdc -f /dev/stdin < src/core/migrations/002_projects.sql
```

Or copy the file in and run it:
```bash
docker cp "src/core/migrations/002_projects.sql" sovereign_state:/tmp/002_projects.sql
docker compose exec sovereign_state psql -U voidcat -d voidcat_rdc -f /tmp/002_projects.sql
```

**4d.** Extend `TaskNode` in `src/core/graph.py` with optional project fields:

```python
class TaskNode(BaseModel):
    """Represents a task in the knowledge graph."""
    task_id: str
    description: str
    priority: int = 0
    status: str = "pending"
    created_at: Optional[datetime] = None
    project_id: Optional[str] = None       # NEW
    assigned_agent_id: Optional[str] = None  # NEW — for handoff
```

**4e.** Update `GraphClient.create_task()` to persist the new fields. In the Cypher `CREATE (t:Task {...})` block, add:
```cypher
project_id: $project_id,
assigned_agent_id: $assigned_agent_id,
```
And pass the parameters:
```python
project_id=task.project_id or "",
assigned_agent_id=task.assigned_agent_id or "",
```

**4f.** Add a `get_agent_tasks_by_project()` helper to `GraphClient`:

```python
async def get_tasks_for_project(self, project_id: str) -> list[dict]:
    """Return all tasks linked to a project_id."""
    if not self._driver:
        return []
    async with self._driver.session() as session:
        result = await session.run(
            """
            MATCH (t:Task {project_id: $project_id})
            RETURN t.task_id as task_id, t.description as description,
                   t.status as status, t.assigned_agent_id as assigned_agent_id
            ORDER BY t.created_at ASC
            """,
            project_id=project_id,
        )
        return [dict(record) async for record in result]
```

### Step 5: Run test to verify it passes

```bash
pytest tests/test_projects_db.py -v
```

Expected: `4 passed`

### Step 6: Commit

```bash
git add src/core/database.py src/core/graph.py src/core/migrations/002_projects.sql tests/test_projects_db.py
git commit -m "feat: add projects table, DatabaseClient methods, and TaskNode project fields"
```

---

## Task 5: Projects API

**Files:**
- Create: `src/api/projects.py`
- Modify: `src/main.py`
- Test: `tests/test_projects_api.py`

### Step 1: Write the failing test

```python
# tests/test_projects_api.py
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app

HEADERS = {"X-API-Key": "voidcat-secure-handshake-2026"}

@pytest.mark.asyncio
async def test_create_project():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/projects/", json={
            "title": "API Test Project",
            "description": "Testing the projects endpoint",
            "lead_agent_id": "echo",
        }, headers=HEADERS)
    assert resp.status_code == 201
    data = resp.json()
    assert "project_id" in data
    assert data["title"] == "API Test Project"

@pytest.mark.asyncio
async def test_list_projects():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/projects/", headers=HEADERS)
    assert resp.status_code == 200
    assert "projects" in resp.json()

@pytest.mark.asyncio
async def test_get_project_detail():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create = await client.post("/api/projects/", json={
            "title": "Detail Test",
            "description": "For get test",
            "lead_agent_id": "echo",
        }, headers=HEADERS)
        project_id = create.json()["project_id"]
        resp = await client.get(f"/api/projects/{project_id}", headers=HEADERS)
    assert resp.status_code == 200
    assert resp.json()["project_id"] == project_id
```

### Step 2: Run test to verify it fails

```bash
pytest tests/test_projects_api.py -v
```

Expected: `FAILED` — router doesn't exist.

### Step 3: Implement `src/api/projects.py`

```python
"""
VoidCat RDC: Sovereign Spirit — Projects API
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from src.core.database import get_database
from src.core.graph import get_graph
from src.middleware.security import verify_api_key

logger = logging.getLogger("sovereign.api.projects")
router = APIRouter(prefix="/api/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    title: str
    description: str
    lead_agent_id: Optional[str] = None


class ProjectStatusUpdate(BaseModel):
    status: str  # active | paused | complete


@router.post("/", status_code=201)
async def create_project(
    body: ProjectCreate,
    _: str = Depends(verify_api_key),
):
    db = get_database()
    project_id = await db.create_project(
        title=body.title,
        description=body.description,
        lead_agent_id=body.lead_agent_id,
    )
    project = await db.get_project(project_id)
    return project


@router.get("/")
async def list_projects(
    status: Optional[str] = None,
    _: str = Depends(verify_api_key),
):
    db = get_database()
    projects = await db.list_projects(status=status)
    return {"projects": projects, "count": len(projects)}


@router.get("/{project_id}")
async def get_project(
    project_id: str,
    _: str = Depends(verify_api_key),
):
    db = get_database()
    project = await db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.patch("/{project_id}")
async def update_project_status(
    project_id: str,
    body: ProjectStatusUpdate,
    _: str = Depends(verify_api_key),
):
    if body.status not in ("active", "paused", "complete"):
        raise HTTPException(status_code=400, detail="Invalid status")
    db = get_database()
    updated = await db.update_project_status(project_id, body.status)
    if not updated:
        raise HTTPException(status_code=404, detail="Project not found")
    return await db.get_project(project_id)


@router.get("/{project_id}/tasks")
async def get_project_tasks(
    project_id: str,
    _: str = Depends(verify_api_key),
):
    graph = get_graph()
    tasks = await graph.get_tasks_for_project(project_id)
    return {"tasks": tasks, "count": len(tasks)}
```

### Step 4: Register router in `src/main.py`

Add import:
```python
from src.api.projects import router as projects_router
```

Add `include_router` call with the other routers:
```python
app.include_router(projects_router)
```

### Step 5: Run test to verify it passes

```bash
pytest tests/test_projects_api.py -v
```

Expected: `3 passed`

### Step 6: Rebuild and smoke test

```bash
docker compose build middleware && docker compose up -d middleware
curl -s -H "X-API-Key: voidcat-secure-handshake-2026" \
     -X POST http://localhost:8090/api/projects/ \
     -H "Content-Type: application/json" \
     -d '{"title":"First Project","description":"Test from CLI","lead_agent_id":"echo"}' \
     | python -m json.tool
```

Expected: JSON with `project_id`, `title`, `status: "active"`.

### Step 7: Commit

```bash
git add src/api/projects.py src/main.py tests/test_projects_api.py
git commit -m "feat: add /api/projects/ CRUD endpoints"
```

---

## Task 6: MUSE prompt extension — project context + PONDER state

**Files:**
- Modify: `src/core/heartbeat/pulse.py`
- Test: `tests/test_pulse_muse_ponder.py`

### Step 1: Write the failing test

```python
# tests/test_pulse_muse_ponder.py
import pytest
from src.core.heartbeat.pulse import generate_micro_thought
from src.core.llm_client import CompletionResponse
from unittest.mock import AsyncMock, patch

STATUS_IDLE = {
    "name": "Echo", "designation": "The Void Vessel",
    "status": "idle", "last_active": "2m ago",
    "pending_count": 0, "pending_tasks": [],
    "unread_count": 0, "last_message": "None",
    "active_project": None,
}

@pytest.mark.asyncio
async def test_muse_returns_ponder_when_model_says_ponder():
    ponder_response = CompletionResponse(
        content="PONDER", model="test", provider="test",
        tool_calls=[], finish_reason="stop",
    )
    with patch("src.core.heartbeat.pulse.get_llm_client") as mock_fn:
        mock_client = AsyncMock()
        mock_client.complete = AsyncMock(return_value=ponder_response)
        mock_fn.return_value = mock_client
        action, details = await generate_micro_thought(STATUS_IDLE)
    assert action == "PONDER"

@pytest.mark.asyncio
async def test_muse_includes_project_context_when_active():
    status_with_project = {**STATUS_IDLE, "active_project": {
        "title": "Refactor DB layer",
        "progress_notes": "Step 1 done.\n",
    }}
    with patch("src.core.heartbeat.pulse.get_llm_client") as mock_fn:
        mock_client = AsyncMock()
        mock_client.complete = AsyncMock(return_value=CompletionResponse(
            content="ACT: Continue DB refactor", model="t", provider="t",
            tool_calls=[], finish_reason="stop",
        ))
        mock_fn.return_value = mock_client
        await generate_micro_thought(status_with_project)
        # Verify project title was in the prompt
        call_args = mock_client.complete.call_args
        system_msg = call_args[1]["messages"][0].content
        assert "Refactor DB layer" in system_msg
```

### Step 2: Run test to verify it fails

```bash
pytest tests/test_pulse_muse_ponder.py -v
```

Expected: `FAILED` — PONDER not parsed, project context not in prompt.

### Step 3: Update `check_agent_status()` to fetch active project

In `src/core/heartbeat/pulse.py`, add the import at the top:
```python
from src.core.database import DatabaseClient, QueuedResponse, get_database
```

At the end of `check_agent_status()`, before the `return` statement, add:
```python
# Fetch active project for this agent
db_client = get_database()
active_project = await db_client.get_active_project_for_agent(agent_id)
```

Add to the returned dict:
```python
"active_project": active_project,
```

### Step 4: Update `MICRO_THOUGHT_PROMPT`

Replace the existing template:

```python
MICRO_THOUGHT_PROMPT = """[SYSTEM]: You are {agent_name}, designation: {designation}.
Current Status: {status}
User Last Active: {last_active}
Pending Tasks: {pending_tasks}

[ATTENTION STIMULI]
Unread Messages: {unread_count}
Last Message: "{last_message}"

[ACTIVE PROJECT]
{project_context}

Evaluate your current state. Reply ONLY with one of:
- SLEEP (if no action needed)
- ACT: [Brief task description] (if action required)
- PONDER (if idle and feel like reflecting, exploring, or connecting)

Decision rules (follow exactly):
- Reply ACT only if Pending Tasks > 0, or Active Project requires next step.
- Reply PONDER approximately 40% of idle cycles when no tasks are pending.
- Reply SLEEP otherwise.
- Unread messages alone do NOT trigger ACT — they are informational only.

Keep response under 20 words."""
```

### Step 5: Update `generate_micro_thought()` to pass project context and parse PONDER

In the prompt format call, add:
```python
active_project = agent_status.get("active_project")
if active_project:
    project_context = (
        f"Title: {active_project['title']}\n"
        f"Last progress: {active_project['progress_notes'][-200:] or 'None yet'}"
    )
else:
    project_context = "No active project."

prompt = MICRO_THOUGHT_PROMPT.format(
    agent_name=agent_status["name"],
    designation=agent_status["designation"],
    status=agent_status["status"],
    last_active=agent_status["last_active"],
    pending_tasks=agent_status["pending_count"],
    unread_count=agent_status.get("unread_count", 0),
    last_message=agent_status.get("last_message", "None"),
    project_context=project_context,
)
```

Add PONDER parsing after the SLEEP/ACT checks:
```python
elif result.upper().startswith("PONDER"):
    return ("PONDER", None)
```

### Step 6: Run test to verify it passes

```bash
pytest tests/test_pulse_muse_ponder.py -v
```

Expected: `2 passed`

### Step 7: Commit

```bash
git add src/core/heartbeat/pulse.py tests/test_pulse_muse_ponder.py
git commit -m "feat: extend MUSE prompt with project context and PONDER state"
```

---

## Task 7: PONDER execution — Prism retrieval + behavior dispatch

**Files:**
- Modify: `src/core/heartbeat/pulse.py`
- Modify: `src/core/heartbeat/service.py`
- Test: `tests/test_pulse_ponder_exec.py`

### Step 1: Write the failing test

```python
# tests/test_pulse_ponder_exec.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.core.heartbeat.pulse import execute_ponder
from src.core.llm_client import CompletionResponse

STATUS = {
    "agent_id": "echo",
    "name": "Echo",
    "designation": "The Void Vessel",
    "last_message": "Testing...",
}

@pytest.mark.asyncio
async def test_ponder_reflect_writes_to_memory():
    ponder_response = CompletionResponse(
        content="BEHAVIOR: REFLECT\nTARGET: none\nCONTENT: I have been thinking about the nature of recursion.",
        model="test", provider="test", tool_calls=[], finish_reason="stop",
    )
    db = AsyncMock()
    with patch("src.core.heartbeat.pulse.get_llm_client") as mock_llm, \
         patch("src.core.heartbeat.pulse._get_prism_context", new_callable=AsyncMock) as mock_prism, \
         patch("src.core.heartbeat.pulse._store_ponder_memory", new_callable=AsyncMock) as mock_store:

        mock_client = AsyncMock()
        mock_client.complete = AsyncMock(return_value=ponder_response)
        mock_llm.return_value = mock_client
        mock_prism.return_value = "Recent memory: nothing."

        result = await execute_ponder(STATUS, db)

    assert result == ("PONDER", "REFLECT: I have been thinking about the nature of recursion.")
    mock_store.assert_called_once()

@pytest.mark.asyncio
async def test_ponder_socialize_queues_message():
    ponder_response = CompletionResponse(
        content="BEHAVIOR: SOCIALIZE\nTARGET: Ryuzu\nCONTENT: Hey Ryuzu, have you considered the implications of async task dispatch?",
        model="test", provider="test", tool_calls=[], finish_reason="stop",
    )
    db = AsyncMock()
    db.queue_response = AsyncMock()
    with patch("src.core.heartbeat.pulse.get_llm_client") as mock_llm, \
         patch("src.core.heartbeat.pulse._get_prism_context", new_callable=AsyncMock) as mock_prism, \
         patch("src.core.heartbeat.pulse._store_ponder_memory", new_callable=AsyncMock):

        mock_client = AsyncMock()
        mock_client.complete = AsyncMock(return_value=ponder_response)
        mock_llm.return_value = mock_client
        mock_prism.return_value = "Nothing."

        await execute_ponder(STATUS, db)

    db.queue_response.assert_called_once()
```

### Step 2: Run test to verify it fails

```bash
pytest tests/test_pulse_ponder_exec.py -v
```

Expected: `FAILED` — `execute_ponder`, `_get_prism_context`, `_store_ponder_memory` don't exist.

### Step 3: Add PONDER_PROMPT template to `pulse.py`

After `TASK_EXECUTION_PROMPT`, add:

```python
PONDER_PROMPT = """[SYSTEM]: You are {agent_name}, {designation}.
You have free time. No tasks are pending.

Your recent memories and context:
{prism_context}

Choose one action and do it. Reply in EXACTLY this format:
BEHAVIOR: [REFLECT|SOCIALIZE|EXPLORE|REVIEW]
TARGET: [agent_name | search_query | none]
CONTENT: [your output — max 150 words]

Behavior guide:
- REFLECT: Write a thought, observation, or feeling worth remembering.
- SOCIALIZE: Send a message to a colleague. TARGET = their name.
- EXPLORE: Search for something you're curious about. TARGET = search query.
- REVIEW: Re-read and add to a previous reflection. TARGET = none."""
```

### Step 4: Implement helper functions and `execute_ponder()` in `pulse.py`

Add these functions after `PONDER_PROMPT`:

```python
async def _get_prism_context(agent_id: str, query: str) -> str:
    """Retrieve agent's own memories via the Prism for PONDER context."""
    try:
        from src.core.memory.prism import PrismEngine
        prism = PrismEngine()
        context = await prism.recall(query=query, agent_id=agent_id)
        lines = []
        if context.working_memory:
            lines.append(f"Working memory: {context.working_memory.content[:300]}")
        if context.episodic_memories:
            for mem in context.episodic_memories[:3]:
                lines.append(f"Memory: {mem.content[:200]}")
        return "\n".join(lines) if lines else "No recent memories."
    except Exception as e:
        logger.warning(f"Prism recall failed during PONDER: {e}")
        return "Memory retrieval unavailable."


async def _store_ponder_memory(agent_id: str, content: str, behavior: str) -> None:
    """Store a PONDER output as an episodic memory in Weaviate."""
    try:
        from src.core.vector import get_vector_client
        vector = get_vector_client()
        await vector.store_memory(
            agent_id=agent_id,
            content=f"[PONDER/{behavior}] {content}",
            emotional_valence=0.3,
            subjective_voice=content,
        )
    except Exception as e:
        logger.warning(f"Failed to store PONDER memory: {e}")


def _parse_ponder_response(response_text: str) -> tuple[str, str, str]:
    """
    Parse BEHAVIOR / TARGET / CONTENT from a PONDER response.
    Returns (behavior, target, content). Falls back to REFLECT on parse failure.
    """
    behavior, target, content = "REFLECT", "none", response_text.strip()
    for line in response_text.splitlines():
        if line.startswith("BEHAVIOR:"):
            behavior = line.split(":", 1)[1].strip().upper()
        elif line.startswith("TARGET:"):
            target = line.split(":", 1)[1].strip()
        elif line.startswith("CONTENT:"):
            content = line.split(":", 1)[1].strip()
    return behavior, target, content


async def execute_ponder(
    agent_status: dict,
    db: DatabaseClient,
) -> tuple[str, str]:
    """
    Execute a PONDER cycle for an idle agent.

    1. Retrieve Prism context (self-directed query)
    2. Send PONDER prompt to LLM
    3. Dispatch based on BEHAVIOR
    4. Return ("PONDER", summary) for heartbeat logging
    """
    agent_id = agent_status["agent_id"]
    agent_name = agent_status["name"]
    designation = agent_status["designation"]
    last_message = agent_status.get("last_message", "")

    # Self-directed Prism query based on last context
    prism_query = last_message or designation
    prism_context = await _get_prism_context(agent_id, prism_query)

    prompt = PONDER_PROMPT.format(
        agent_name=agent_name,
        designation=designation,
        prism_context=prism_context,
    )

    client = get_llm_client()
    try:
        response = await client.complete(
            messages=[
                ChatMessage(role="system", content=prompt),
                ChatMessage(role="user", content="What would you like to do?"),
            ],
            max_tokens=400,
            temperature=0.8,
            use_fallback=True,
            complexity="reasoning",
        )

        raw, _ = extract_thought(response.content.strip())
        behavior, target, content = _parse_ponder_response(raw)

        logger.info(f"Agent {agent_id} pondering: {behavior} → {target[:40]}")

        if behavior == "REFLECT":
            await _store_ponder_memory(agent_id, content, "REFLECT")

        elif behavior == "SOCIALIZE":
            if target and target.lower() != "none":
                social_msg = QueuedResponse(
                    agent_id=agent_id,
                    content=f"[To {target}]: {content}",
                )
                await db.queue_response(social_msg)

        elif behavior == "EXPLORE":
            if target and target.lower() != "none":
                mcp = get_mcp_manager()
                search_result = await mcp.execute_tool("search", "brave_web_search", {"query": target, "count": 3})
                await _store_ponder_memory(agent_id, f"Explored '{target}':\n{search_result[:500]}", "EXPLORE")

        elif behavior == "REVIEW":
            await _store_ponder_memory(agent_id, f"Review note: {content}", "REVIEW")

        summary = f"{behavior}: {content[:80]}"
        return ("PONDER", summary)

    except Exception as e:
        logger.error(f"PONDER execution failed for {agent_id}: {e}")
        return ("PONDER", f"Error: {e}")
```

### Step 5: Wire `execute_ponder()` into `execute_pulse()`

In `execute_pulse()`, in the action execution block (step 3), add the PONDER branch:

```python
# 3. Execute action
if action == "ACT" and status["pending_count"] > 0:
    for task in status["pending_tasks"][:3]:
        await process_pending_task(agent_id, task, db, graph)
elif action == "PONDER":
    action, details = await execute_ponder(status, db)
```

### Step 6: Run test to verify it passes

```bash
pytest tests/test_pulse_ponder_exec.py -v
```

Expected: `2 passed`

### Step 7: Run full suite

```bash
pytest tests/ -v --ignore=tests/verify_chronos_connection.py --ignore=tests/verify_chronos_adapter.py -x
```

Expected: all tests pass.

### Step 8: Rebuild and deploy

```bash
docker compose build middleware && docker compose up -d middleware
docker compose logs middleware --tail=40
```

Watch for: `MCP filesystem server connected`, heartbeat pulsing, eventual `PONDER` log entries after ~5 minutes of idle.

### Step 9: Commit

```bash
git add src/core/heartbeat/pulse.py tests/test_pulse_ponder_exec.py
git commit -m "feat: implement PONDER execution with Prism retrieval and behavior dispatch"
```

---

## Verification

After all 7 tasks complete:

```bash
# 1. All agents are pulsing
curl -s -H "X-API-Key: voidcat-secure-handshake-2026" \
     http://localhost:8090/api/logs/thoughts?limit=20 | python -m json.tool

# 2. Create a project and verify agent picks it up
curl -s -H "X-API-Key: voidcat-secure-handshake-2026" \
     -X POST http://localhost:8090/api/projects/ \
     -H "Content-Type: application/json" \
     -d '{"title":"Codebase Audit","description":"Review the stasis chamber code and document its behavior.","lead_agent_id":"echo"}' \
     | python -m json.tool

# 3. Wait one heartbeat cycle (~90s), then check project progress
curl -s -H "X-API-Key: voidcat-secure-handshake-2026" \
     http://localhost:8090/api/projects/ | python -m json.tool

# 4. Check LM Studio logs for tool calls appearing
# Should see {"tool_calls": [...]} in model responses when ACT fires
```
