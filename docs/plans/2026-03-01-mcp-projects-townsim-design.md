# Design: MCP Wiring + Project System + Town Sim
**Date:** 2026-03-01
**Status:** Approved
**Approach:** Option A — Single-shot tool call per ACT cycle

---

## Problem Statement

Agents currently run in a vacuum. The MUSE/ACT/SLEEP heartbeat loop fires correctly, but
when an agent decides ACT it does nothing real — it marks a task complete and queues a
canned response. The MCP infrastructure (client, server registry, adapters) exists but is
never initialized and is not reachable from the heartbeat. The LLM client has no tool-call
support. There is no mechanism for issuing long-term goals or tracking progress against them.
When no tasks are queued, agents do nothing.

This design resolves all three gaps in a single build:
1. Wire MCP tools into the agent loop
2. Add a Project/Goal system for long-running background work
3. Add Town Sim idle behavior with self-directed memory retrieval

---

## Section 1: MCP Wiring

### 1a. LLMClient — tool call support

`src/core/llm_client.py` `complete()` gains an optional `tools` parameter.

- Format: OpenAI function-call format `[{"type": "function", "function": {"name", "description", "parameters"}}]`
- If tools are passed and the model returns `tool_calls` in the response, these are surfaced in the `LLMResponse` object alongside `content`
- No change to call sites that don't pass tools — fully backwards compatible
- Local models via LM Studio (Qwen3, etc.) already support this format

```python
# New LLMResponse fields
tool_calls: list[dict]  # [{id, function: {name, arguments}}] or []

# New complete() signature
async def complete(
    self,
    messages: list[ChatMessage],
    max_tokens: int = 500,
    temperature: float = 0.6,
    use_fallback: bool = True,
    complexity: str = "direct",
    tools: list[dict] | None = None,   # NEW
) -> LLMResponse:
```

### 1b. MCPManager singleton + startup

`src/mcp/client.py` gains a module-level singleton pattern matching the rest of the codebase:

```python
_mcp_manager: MCPManager | None = None

def get_mcp_manager() -> MCPManager:
    global _mcp_manager
    if _mcp_manager is None:
        _mcp_manager = MCPManager()
    return _mcp_manager
```

`src/main.py` lifespan connects servers at startup:

```python
mcp = get_mcp_manager()
await mcp.connect_server("filesystem")
await mcp.connect_server("search")   # only if BRAVE_SEARCH_API_KEY is set
# chronos skipped — known broken path issue (open issue #2)
```

`MCPManager` gains a helper that returns tools in OpenAI format ready to pass to `complete()`:

```python
def get_tools_for_llm(self) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["schema"],
            }
        }
        for t in self.available_tools
    ]
```

### 1c. ACT phase rewrite — single-shot tool call

`pulse.py` `process_pending_task()` is rewritten. Current behavior (mark complete, queue
canned response) is replaced with:

1. Build a task execution prompt from the task description + project context
2. Call `llm_client.complete()` with `tools=mcp_manager.get_tools_for_llm()`
3. If response contains `tool_calls`: execute the first call via `mcp_manager.execute_tool()`, feed result back to LLM for synthesis (one follow-up call, no tools this time)
4. If no tool calls: treat LLM response as the direct result
5. Store synthesis as task result in Neo4j, queue as response for the user

**Max one tool call per ACT cycle** (Option A). This keeps cycles predictable, auditable, and bounded. Can evolve to chaining (ReAct) later.

```
Task prompt structure:
[SYSTEM] You are {agent_name}. You are working on: "{task_description}"
Project context: "{project_progress_notes[-500:]}"
Available tools: {tool_list}
Decide the single most useful action to take right now.
If no tool is needed, respond directly.
```

---

## Section 2: Project System

### 2a. Data model

**New Postgres table — `projects`:**

```sql
CREATE TABLE projects (
    project_id  TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    title       TEXT NOT NULL,
    description TEXT NOT NULL,
    lead_agent_id TEXT REFERENCES agents(agent_id),
    status      TEXT NOT NULL DEFAULT 'active',  -- active | paused | complete
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    progress_notes TEXT DEFAULT ''  -- append-only running log
);
```

**Neo4j TaskNode extensions:**
- Add `project_id: str` — links task to parent project
- Add `assigned_agent_id: str` — enables cross-agent handoff (agent A creates task for agent B)

### 2b. Handoff mechanism

When an agent completes a task and determines the next step requires a different specialist,
it creates a new Neo4j task with `assigned_agent_id` set to the target agent. The target
agent's next MUSE cycle will find this pending task and pick it up. No central dispatcher
needed — the task graph itself routes work.

Agent specialties are declared in their system prompt context. The LLM naturally determines
handoff targets: Albedo gets architecture tasks, Pandora gets debugging tasks, etc.

### 2c. MUSE prompt extension

The MUSE state evaluation prompt gets one addition:

```
Active Projects: {active_project_count}
Current Project: "{current_project_title}" — last progress: "{last_progress_snippet}"
```

Decision rule added: `ACT if assigned project tasks > 0 OR (active project exists and
agent should generate next step).`

If the agent has an active project but no pending tasks for it, it ACTs to generate the
next task itself and write it to the graph.

### 2d. API endpoints

```
POST   /api/projects/              Create project, assign lead agent
GET    /api/projects/              List all with status + progress summary
GET    /api/projects/{id}          Full detail: description, task history, progress notes
PATCH  /api/projects/{id}          Update status (pause/resume/complete)
GET    /api/projects/{id}/tasks    All tasks for project with status
```

Progress notes are append-only — each task completion appends a timestamped line. The full
note history is available in the project detail endpoint.

---

## Section 3: Town Sim / PONDER

### 3a. New heartbeat state

MUSE gains a third output: `PONDER` (alongside SLEEP and ACT).

Decision rule: `PONDER if pending_tasks == 0 AND no active project tasks AND random() < PONDER_RATE`

`PONDER_RATE` defaults to `0.4` (env var `HEARTBEAT_PONDER_RATE`). Not every idle cycle
triggers a ponder — some cycles just SLEEP. This prevents agents from flooding memory with
low-quality idle outputs.

### 3b. Prism retrieval — self-directed

Before the PONDER prompt is built, a Prism memory retrieval runs for the agent using a
**self-directed query** derived from their last action or last written memory. This means
retrieval is contextually relevant rather than a fixed recency dump.

```python
# Query derived from last heartbeat context
prism_query = agent_status.get("last_thought") or agent_status.get("designation")
memories = await prism.retrieve(agent_id, query=prism_query, limit=5)
```

The agent sees:
- Their own recent memories from Weaviate (full subjective voice intact — no valence stripping for self-reads)
- Recent task results from Neo4j (what they've actually done)
- Fast Stream (last few messages)

This allows PONDER cycles to compound: a thread started in one cycle can be picked up in
a later cycle when a related memory surfaces.

### 3c. PONDER behaviors

The PONDER prompt asks the agent to choose one behavior and execute it:

| Behavior | What happens |
|----------|-------------|
| **Reflect** | Writes a thought/observation to Weaviate memory with `emotional_valence` set |
| **Socialize** | Queues a message to another agent (target chosen by LLM from agent list) |
| **Explore** | Calls the search tool on a topic of the agent's choosing |
| **Review** | Reads and comments on a previous memory or task output — appends to it |

The behavior chosen and its output are logged in the heartbeat cycle table with
`action = "PONDER"` and `details = "{behavior}: {summary}"`. This makes idle behavior
fully visible in the dashboard.

### 3d. PONDER prompt

```
[SYSTEM] You are {agent_name}, {designation}.
You have free time. No tasks are pending.

Your recent memories:
{prism_memories}

Your recent work:
{recent_task_results}

Choose one of the following and do it:
- REFLECT: Write a thought, observation, or feeling to your memory.
- SOCIALIZE: Send a message to one of your colleagues: {agent_list}
- EXPLORE: Search for something you're curious about.
- REVIEW: Re-read something you wrote before and add to it.

Reply with:
BEHAVIOR: [REFLECT|SOCIALIZE|EXPLORE|REVIEW]
TARGET: [agent_name | search query | memory_id | none]
CONTENT: [your output — max 150 words]
```

Temperature is raised to `0.8` for PONDER vs `0.6` for task work — more generative,
less decisive.

---

## Build Sequence

These are ordered by dependency. Each step is independently deployable.

1. **`LLMClient` tool support** — add `tools` param + parse `tool_calls` in response
2. **`MCPManager` singleton + lifespan init** — filesystem + search connected at startup
3. **`process_pending_task()` rewrite** — single-shot tool call loop
4. **Projects Postgres schema** — migration + `DatabaseClient` methods
5. **Projects API** — 5 endpoints in new `src/api/projects.py`
6. **MUSE prompt extension** — project context + PONDER state
7. **PONDER execution** — Prism retrieval + behavior dispatch
8. **Dashboard project view** — surface projects + PONDER logs in Tether (deferred to dashboard phase)

Steps 1–3 unlock real tool use. Steps 4–5 give agents something to work toward.
Steps 6–7 complete the autonomous loop. Step 8 is visibility — useful but not blocking.

---

## What Is Not In This Design

- **Multi-tool chaining (ReAct)** — deferred, can be added to `process_pending_task()` later
- **Chronos MCP server** — blocked on broken path issue, fix separately
- **Cross-agent memory sharing** — Prism already handles this with valence stripping; no changes needed
- **Agent-to-agent message processing** — SOCIALIZE queues a message; the receiving agent reads it in their normal unread messages flow, no new infrastructure needed
- **Dashboard agent detail panels** — separate design doc, deferred until agents are actually doing things worth watching
