# Sovereign Spirit - AI Agent Instructions

**Sovereign Spirit** is a FastAPI backend (port **8090**) for autonomous AI agents with heartbeat-driven autonomy, persona switching, and three-tier memory. Use root `docker-compose.yml` (not `config/docker-compose.yml` -- that's stale).

## Stack & Ports

| Service | Internal | External | Container |
|---------|----------|----------|-----------|
| FastAPI | 8090 | 8090 | `sovereign_middleware` |
| PostgreSQL 15 + pgvector | 5432 | (not exposed) | `sovereign_state` |
| Neo4j 5 | 7687, 7474 | same | `sovereign_graph` |
| Weaviate | **8080** | **8095** | `sovereign_memory` |
| Redis 7 | 6379 | 6379 | `sovereign_cache` |

Weaviate port mismatch is the most common config bug: inside Docker use `http://weaviate:8080`, from host use `localhost:8095`.

Flutter Web dashboard is served at `/` via `StaticFiles` mount. Real-time state via WebSocket at `/ws/dashboard`.

## Architecture Patterns

**Valence Stripping** -- When Agent A reads Agent B's memories, `subjective_voice` is emptied and `emotional_valence` reset to `0.0` to prevent personality bleed. Use `process_memory_batch(memories, requesting_agent_id)` from `src/middleware/valence_stripping.py`. Case-insensitive `author_id` matching, uses `dataclasses.replace()`. Any new memory endpoint must apply this filter.

**Heartbeat Autonomy** -- Each agent runs a 60-90s jittered background loop: MUSE (evaluate state) -> ACT (execute tasks, max 3/cycle) -> SLEEP. Core cycle in `src/core/heartbeat/pulse.py`, daemon in `src/core/heartbeat/service.py`. Cycles must be idempotent and never block the event loop. Supports `<think>...</think>` tags for internal monologue.

**Bifrost LLM Routing** -- `LLMClient` (`src/core/llm_client.py`) routes inference across Ollama, LM Studio, OpenRouter, and OpenAI. All use OpenAI-compatible `/v1/chat/completions`. Pass `complexity="direct"` for local-first routing or `complexity="reasoning"` for cloud-capable. Automatic fallback chain with health checks per provider.

**The Prism (Three-Tier Memory)** -- Fast Stream (Redis: working memory, last 10 messages), Deep Well (Weaviate: episodic memory with vector search + emotional valence), Crystalline Web (Neo4j: knowledge graph, tasks, causality). Retrieved in parallel via `asyncio.gather()` in `src/core/memory/prism.py`. Valence stripping applied inline during Deep Well retrieval.

**Stasis Chamber** -- Agent state freeze/thaw for cold boot persistence. Atomic writes (`.tmp` then rename) with `.ptr` pointer files in `stasis_tanks/`. API at `/api/stasis/`. Implementation: `src/core/memory/stasis_chamber.py`.

## Coding Conventions

- **Timestamps**: `datetime.now(timezone.utc)` always -- never `datetime.now()` or `datetime.utcnow()`
- **Service access**: Use singletons -- `get_database()`, `get_graph()`, `get_llm_client()`, `get_cache()`, `get_vector_client()`, `get_identity_manager()`
- **Input sanitization**: All user input through `sanitize_message_content()` / `sanitize_agent_name()` from `src/middleware/security.py`
- **Logging**: `logging.getLogger()` only -- never `print()`. Security middleware fails closed (missing API key -> 401)
- **Database**: `async with db.session()` + `text()` for SQL, parameterized queries only

## Warnings

- Never expose a foreign agent's `subjective_voice` or `emotional_valence` without running through `process_memory_batch()` -- this is the Soul Bleed invariant
- Never use `config/docker-compose.yml` -- root `docker-compose.yml` is canonical
- Never commit secrets to `config/llm_providers.yaml` -- use `.env` and `${ENV_VAR}` references
- Do not delete or hand-edit `stasis_tanks/` -- contains live agent state for resurrection
- WebSocket at `/ws/dashboard` accepts GOD_MODE commands (GOD_SYNC, GOD_MOOD, GOD_STIMULI) -- understand the Throne protocol in `src/main.py` before adding commands
