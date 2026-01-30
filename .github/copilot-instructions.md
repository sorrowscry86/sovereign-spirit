---
description: AI rules derived by SpecStory from the project AI interaction history
globs: *
---

## PROJECT OVERVIEW

**Sovereign Spirit** is a headless, multi-agent system (MAS) implementing **persistent, autonomous AI agents** with true digital sovereignty. The system is organized around **The Memory Prism** (three-tier memory architecture) and **The Heartbeat** (autonomous event loops). Version 4.0 operates in "headless" mode—the backend (Python/FastAPI) is logic-sovereign and decoupled from UI clients.

**Key Docs:**
- [VoidCat Sovereign Architecture v4.md](../docs/VoidCat%20Sovereign%20Architecture%20v4.md) — Technical spec (living)
- [VoidCat RDC Whitepaper](../docs/VoidCat%20RDC_%20A%20Technical%20Whitepaper%20for%20a%20Multi-Agent%20System%20with%20Persistent%20Memory.md) — Research foundation
- [Phase 1 Roadmap](../docs/VoidCat%20Phase%201%20Roadmap.md) — Implementation schedule

## ARCHITECTURE: THE MEMORY PRISM & HEARTBEAT

The system uses three tightly-coupled memory layers:

1. **Fast Stream (Redis 7)** — Working memory. Current task focus, active context. AOF persistence enabled.
2. **Deep Well (Weaviate 8090)** — Episodic memory. Raw experiences with **emotional valence** (float -1.0 to +1.0). Semantic search retrieval.
3. **Crystalline Web (Neo4j 7687)** — Knowledge graph. Logic, causality, relationships. Node types: `:Agent`, `:Task`, `:File`, `:Concept`.

**The Heartbeat** (`src/core/pulse.py`): 60-90s autonomous loops per agent. Each cycle: **Sense** (Redis streams, metrics) → **Think** (low-token monologue) → **Act** (tool execution, graph update, message queue) → **Sleep**.

## CODE ORGANIZATION

```
src/
├── main.py              # FastAPI entry point, lifespan management
├── api/                 # Request routers (agents, graph, config)
├── core/                # Business logic
│   ├── database.py      # PostgreSQL client (async SQLAlchemy)
│   ├── vector.py        # Weaviate proxy client
│   ├── graph.py         # Neo4j graph client
│   ├── heartbeat/       # Pulse & autonomous loops
│   ├── identity/        # Agent identity/persona management
│   ├── inference/       # LLM client (Ollama integration)
│   └── memory/          # Memory assembly & retrieval
├── middleware/
│   ├── valence_stripping.py  # CRITICAL: Strips emotional metadata from inter-agent memories
│   └── security.py      # API key, rate limiting, input sanitization
├── cli/                 # CLI commands for admin ops
└── mcp/                 # Module Context Protocol (MCP) for autonomous tool execution
```

## CRITICAL PATTERNS & CONVENTIONS

### 1. Valence Stripping (Soul Bleed Prevention)
**Problem:** Without isolation, agents adopting other agents' emotional memories could lose individuality ("soul bleed").

**Solution:** [valence_stripping.py](../src/middleware/valence_stripping.py) intercepts memory queries:
- If `requesting_agent_id == memory.author_id`: return memory **intact** (subjective voice + emotional valence)
- If `requesting_agent_id != memory.author_id`: return **sanitized** (objective fact only, valence → 0.0)

**When modifying:** Preserve case-insensitive author matching. Always use `dataclasses.replace()` for efficiency.

### 2. Heartbeat Autonomy
The heartbeat loop is **async-first** and non-blocking. When implementing agent behaviors:
- Never block the event loop. Use `asyncio` throughout.
- Heartbeat frequency is jittered (60-90s) to avoid thundering herd.
- Each cycle must be **idempotent** and tolerant of message queue failures.

### 3. API Endpoint Security: Fail Closed
From `src/middleware/security.py`:
- **API Key**: Disabled by default (`SOVEREIGN_API_KEY_ENABLED=false`). When enabled, request without valid key → 401 Unauthorized.
- **Rate Limiting**: Enabled by default. Defaults: 60 requests per 60s window per IP.
- **Input Sanitization**: All message content + agent IDs must pass `sanitize_message_content()` before storage.
- **Database Constraints**: Request bodies are mandatory. Never use default `None` for required params—raise `HTTPException(400)` instead.

### 4. Type Safety & Async First
- **All Python code must be fully type-hinted** (PEP 484). Use `typing.Optional`, `typing.List`, etc.
- Async throughout. Never use sync database calls in FastAPI handlers—use `async with` and `await`.

### 5. Autonomous Tool Execution (Module Context Protocol)
The Sovereign Spirit Core can:
- Discover local MCP servers (Filesystem, Git, Search).
- Connect to them via stdio/SSE.
- Execute tools when the LLM emits a tool-call token.

See `src/mcp/` for implementation details. Key components:
- Configuration (`src/mcp/config.py`): Defines the registry of available MCP servers.
- Client Manager (`src/mcp/client.py`): Manages MCP connections, aggregates tools, routes tool calls.
- Integration (`src/inference/engine.py`): Injects available MCP tools into the system prompt and intercepts tool calls for execution.

## TYPICAL WORKFLOWS

### Running the Stack
```bash
# Docker Compose (all services)
docker-compose -f config/docker-compose.yml up

# Services: FastAPI (8000), Weaviate (8090), Neo4j (7474/7687), PostgreSQL (5432), Redis (6379), Ollama (11434)
```

### Adding a New Agent Endpoint
1. Define request/response Pydantic models in [src/api/agents.py](../src/api/agents.py).
2. Fetch agent identity via `get_identity_manager().get_agent(agent_id)`.
3. Apply valence stripping to memory results before returning.
4. Validate & sanitize inputs. Raise `HTTPException(400)` if validation fails.

### Modifying Memory Retrieval
1. Query Weaviate via `get_vector_client().search(query, agent_id)`.
2. **Always** run results through `process_memory_batch(memories, requesting_agent_id)`.
3. Never expose raw `emotional_valence` to unauthorized agents.

## ENVIRONMENT VARIABLES (Configuration & Tuning)

**Core Service Configuration:**
- `LOG_LEVEL` — Logging verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR`. Default: `INFO`.
- `SOVEREIGN_API_KEY_ENABLED` — Enable/disable API key auth. Default: `false` (disabled for dev).
- `SOVEREIGN_API_KEY` — API key value when `_ENABLED=true`. Must be set if enabled.
- `SOVEREIGN_RATE_LIMIT_ENABLED` — Enable rate limiting. Default: `true`.
- `SOVEREIGN_RATE_LIMIT_REQUESTS` — Requests per window. Default: `60`.
- `SOVEREIGN_RATE_LIMIT_WINDOW` — Time window in seconds. Default: `60`.

**Database (PostgreSQL):**
- `DATABASE_URL` — Async connection string. Default: `postgresql+asyncpg://voidcat:sovereign_spirit@postgres:5432/voidcat_rdc`.
- `DB_POOL_SIZE` — Base connection pool size. Default: `5`.
- `DB_POOL_OVERFLOW` — Max overflow connections. Default: `10`.
- `DB_POOL_TIMEOUT` — Acquire timeout (seconds). Default: `30`.
- `DB_POOL_RECYCLE` — Connection recycle time (seconds). Default: `1800` (30 min).

**Vector DB (Weaviate):**
- `VOIDC_WEAVIATE_URL` — Weaviate endpoint. Default: `http://weaviate:8090`.

**Inference (LLM Providers):**
- `OLLAMA_HOST` — Ollama endpoint. Default: `http://localhost:11434`.
- `OLLAMA_MODEL` — Model name/tag. Default: `mistral:7b-instruct-v0.2-q4_K_M`.
- `LM_STUDIO_HOST` — LM Studio endpoint. Default: `http://localhost:1234`.
- `OPENROUTER_MODEL` — OpenRouter model ID. Default: `mistralai/mistral-7b-instruct`.
- `OPENROUTER_API_KEY` — OpenRouter API key (required if using OpenRouter).
- `OPENAI_MODEL` — OpenAI model. Default: `gpt-3.5-turbo`.
- `OPENAI_API_KEY` — OpenAI API key (required if using OpenAI).

## INFERENCE & LLM CLIENT (Model Integration)

From [src/core/llm_client.py](../src/core/llm_client.py):

**Supported Providers:**
- `ollama` — Local, free. Best for consumer GPUs. Supports quantized models (Q4, Q5).
- `lm_studio` — Local GUI wrapper. Uses currently loaded model.
- `openrouter` — Cloud-based routing to Mistral, Llama, etc. Requires API key.
- `openai` — GPT-3.5, GPT-4. Requires API key.

**When Integrating LLM Calls:**
1. Get provider config from `DEFAULT_PROVIDERS` dict in `llm_client.py`.
2. Use `LLMClient.complete()` for single completions, `stream()` for streaming.
3. Always pass agent system prompt via `CompletionRequest.messages[0]` with `role="system"`.
4. Respect `max_tokens` and `temperature` from agent identity; override only if necessary.
5. Handle timeouts gracefully—fallback to cached response or retry with exponential backoff.

**Model Selection Philosophy:**
- **Default (Ollama):** Mistral 7B for balance of speed/quality on consumer hardware.
- **Quality Priority:** Use OpenRouter or OpenAI for complex reasoning tasks.
- **Speed Priority:** Use local Ollama with Q4 quantization to minimize latency.
- **GPU Memory:** Track VRAM usage via `LOG_LEVEL=DEBUG` output; adjust model size if OOM.

**Example: Adding a New Provider**
```python
# In DEFAULT_PROVIDERS, add:
"my_provider": ProviderConfig(
    name="my_provider",
    provider_type=ProviderType.OLLAMA,  # or other type
    endpoint=os.getenv("MY_ENDPOINT", "http://default"),
    model=os.getenv("MY_MODEL", "default-model"),
    api_key=os.getenv("MY_API_KEY"),
)
```

## PROJECT-SPECIFIC STANDARDS

- **Database**: PostgreSQL 15 (async). Connection pooling: 5-10 concurrent connections.
- **Vector DB**: Weaviate on port 8090. Queries return `MemoryObject` with 6 fields (id, author_id, objective_fact, subjective_voice, emotional_valence, timestamp).
- **Graph DB**: Neo4j on 7687. Use Cypher queries; avoid N+1 patterns.
- **Naming**: Snake_case for Python, camelCase for JavaScript (src/web_ui).
- **Agent Identity**: Stored in PostgreSQL `agents` table. Unique on `id` (UUID), `name` (indexed for lookups).

## TESTING & DEBUGGING

- **No automated CI/CD yet** (scheduled Phase 7). Manual verification is mandatory.
- Test with `pytest` when tests exist. Priority: memory isolation (valence stripping), heartbeat stability, API security.
- Check logs via `logging.getLogger()`. Set `LOG_LEVEL=DEBUG` env var for verbose output.
- Docker Compose logs: `docker-compose logs -f {service_name}`.

## PROJECT DOCUMENTATION & CONTEXT SYSTEM

- Use `.github/copilot-instructions.md` to guide AI coding agents. This file should contain essential knowledge to help an AI agent be immediately productive in this codebase.
- Key files/directories should be referenced in `.github/copilot-instructions.md` as examples of important patterns.

## FINAL DOs AND DON'Ts

**DOs:**
- Always ensure request bodies are mandatory. Avoid default `None` values without validation.
- Always validate and sanitize user inputs (agent IDs, message content) via `sanitize_message_content()`.
- Always use async/await—never block the event loop.
- Always type-hint all Python code. Full PEP 484 compliance.
- Always preserve emotional valence semantics when modifying memory structures.
- **Always** fail closed on security misconfigurations (missing API key, malformed requests).

**DON'Ts:**
- Never expose a foreign agent's subjective voice or emotional valence without stripping.
- Never use sync database calls in async contexts.
- Never create unused code—delete immediately.
- Don't assume the UI layer drives logic. Logic is server-side sovereign.