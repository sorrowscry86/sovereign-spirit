# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

**Sovereign Spirit** is the autonomous agent backend for the VoidCat RDC. Persistent AI agents with heartbeat-driven autonomy, subjective memory, persona switching, and MCP tool access. FastAPI on port **8090**. Phase III (Agency) working toward Phase IV (Sovereignty).

## How to Run

```bash
# Docker (production) — uses root docker-compose.yml (NOT config/docker-compose.yml)
docker compose up -d

# Local dev
pip install -r requirements.txt
uvicorn src.main:app --host 0.0.0.0 --port 8090 --reload

# Tests
pytest tests/ -v                              # all tests
pytest tests/test_agent_api.py -v             # single file
pytest tests/test_agent_api.py -k "test_name" # single test
```

Environment: copy `.env.example` to `.env` and fill in secrets.

## Technology Stack

| Service | Container | Internal | External |
|---------|-----------|----------|----------|
| FastAPI + Uvicorn | `sovereign_middleware` | 8090 | 8090 |
| PostgreSQL 15 + pgvector | `sovereign_state` | 5432 | not exposed |
| Neo4j 5 | `sovereign_graph` | 7687 | 7474, 7687 |
| Weaviate | `sovereign_memory` | **8080** | **8095** |
| Redis 7 | `sovereign_cache` | 6379 | 6379 |
| LLM Inference | host machine | — | LM Studio / Ollama / OpenRouter |

**Weaviate port mismatch is the most common config bug:** inside Docker use `http://weaviate:8080`, from host use `localhost:8095`.

Flutter Web dashboard served at `/` via `StaticFiles` mount. Real-time state via WebSocket at `/ws/dashboard`.

## Architecture

**Heartbeat** — 60-90s jittered autonomous loop per agent: MUSE (evaluate state) → ACT / PONDER / SLEEP. ACT executes up to 3 pending tasks per cycle via MCP tool calls. PONDER triggers ~40% of idle cycles — the agent runs a Prism self-recall then chooses REFLECT (store memory), SOCIALIZE (message another agent), EXPLORE (web search via MCP), or REVIEW (revisit past reflections). Core cycle in `src/core/heartbeat/pulse.py`, daemon in `src/core/heartbeat/service.py`. Cycles must be idempotent. Supports `<think>...</think>` tags for internal monologue.

**The Prism (Three-Tier Memory)** — Fast Stream (Redis: working memory, last 10 messages), Deep Well (Weaviate: episodic memory with vector search + emotional valence), Crystalline Web (Neo4j: knowledge graph, causality). Retrieved in parallel via `asyncio.gather()` in `src/core/memory/prism.py`.

**Valence Stripping** — When Agent A reads Agent B's memories, `subjective_voice` is emptied and `emotional_valence` reset to `0.0` to prevent Soul Bleed. Use `process_memory_batch(memories, requesting_agent_id)` from `src/middleware/valence_stripping.py`. **Any new memory endpoint must apply this filter.**

**MCP Tool Access** — Agents can call external tools via the Model Context Protocol. `MCPManager` in `src/mcp/client.py` connects to MCP servers at startup (filesystem always, search if `BRAVE_SEARCH_API_KEY` set). During ACT cycles, `process_pending_task()` passes available tools to the LLM; if the model returns a `tool_call`, the tool is executed and the result synthesized. Single-shot: one tool call per cycle.

**Bifrost LLM Routing** — `LLMClient` in `src/core/llm_client.py` routes inference across providers (all OpenAI-compatible `/v1/chat/completions`). Pass `complexity="direct"` for local-first routing, `complexity="reasoning"` for cloud-capable. Pass `tools=` for function calling (forces HTTP path, bypasses LM Studio SDK). Automatic fallback chain with health checks.

**Projects** — Long-running goals stored in Postgres (`projects` table). CRUD API at `/api/projects/`. Each project has a `lead_agent_id`, status (`active`/`paused`/`complete`), and `progress_notes` (append-only log). Active projects appear in the MUSE prompt so agents can reason about their goals. Tasks in Neo4j can carry `project_id` and `assigned_agent_id`.

**Stasis Chamber** — Agent state freeze/thaw for cold boot persistence. Atomic writes (`.tmp` then rename) with `.ptr` pointer files in `stasis_tanks/`. API at `/api/stasis/`. Implementation: `src/core/memory/stasis_chamber.py`.

**Fluid Persona** — Keyword-triggered spirit switching (e.g., "security" → Roland, "design" → Ryuzu). Middleware in `src/middleware/persona.py`.

**The Throne** — Flutter Web dashboard at `/`. WebSocket at `/ws/dashboard` accepts GOD_MODE commands: `GOD_SYNC` (persona switch), `GOD_MOOD` (mood set), `GOD_STIMULI` (inject thought). Understand the Throne protocol in `src/main.py` before adding commands. STATE_UPDATE broadcasts all agents every 2 seconds.

## Code Patterns

**Singleton getters** — All shared infrastructure uses module-level singletons. Never instantiate directly:
```python
db = get_database()          # src/core/database.py
graph = get_graph()          # src/core/graph.py
client = get_llm_client()    # src/core/llm_client.py
cache = get_cache()          # src/core/cache.py
vector = get_vector_client() # src/core/vector.py
mgr = get_identity_manager() # src/core/identity/manager.py
mcp = get_mcp_manager()      # src/mcp/client.py
prism = get_prism()          # src/core/memory/prism.py
```

**Database queries** — Raw SQL with `text()`, not ORM. Parameterized queries only. Always use the async context manager:
```python
async with db.session() as session:
    result = await session.execute(text("SELECT ..."), {"param": value})
```

**Router registration** — Explicit includes in `src/main.py`. Static file mount must come AFTER all API routes to avoid conflicts.

**Lifespan** — All startup/shutdown in the `lifespan()` context manager in `src/main.py`. Individual resource cleanup is try/excepted so one failure doesn't block others.

**Input sanitization** — All user input through `sanitize_message_content()` / `sanitize_agent_name()` from `src/middleware/security.py`. Security middleware fails closed (missing API key → 401).

## Coding Standards

- `datetime.now(timezone.utc)` always — never `datetime.now()` or `datetime.utcnow()`
- Async first — never block the event loop
- Type hints on all function signatures
- `logging.getLogger()` only — never `print()`
- snake_case for Python, kebab-case for web assets
- Black for formatting, PEP 8 for style
- Commit prefixes: `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`

## Warnings

- Never expose a foreign agent's `subjective_voice` or `emotional_valence` without `process_memory_batch()` — this is the Soul Bleed invariant
- Never use `config/docker-compose.yml` — root `docker-compose.yml` is canonical
- Never commit secrets to `config/llm_providers.yaml` — use `.env` and `${ENV_VAR}` references
- Do not delete or hand-edit `stasis_tanks/` — contains live agent state for resurrection
- Do not hardcode Windows paths in adapters — use environment variables

## Known Issues

1. **Frontend service commented out in root `docker-compose.yml`** — React UI deleted, Flutter Web is embedded. Comment block can be removed.
2. **Dead API key in git history** — `config/llm_providers.yaml` history contains a revoked key. Clean with BFG if repo goes public.
