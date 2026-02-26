# CLAUDE.md — Sovereign Spirit

> Canonical reference for Claude Code sessions in this repository.
> Last verified: 2026-02-26 by Vivy (Context Integrator).

## What This Is

**Sovereign Spirit** is the autonomous agent backend for the VoidCat RDC system. It provides persistent AI agents with heartbeat-driven autonomy, subjective memory, persona switching, and MCP tool access. Phase III (Agency) — working toward Phase IV (Sovereignty).

## Technology Stack

| Component | Technology | Port | Container |
|-----------|-----------|------|-----------|
| API Gateway | FastAPI + Uvicorn | **8090** | `sovereign-middleware` |
| State DB | PostgreSQL 15 + pgvector | 5432 (internal) | `sovereign-postgres` |
| Graph DB | Neo4j 5 | 7474, 7687 | `sovereign-neo4j` |
| Vector DB | Weaviate | 8095 (external), 8080 (internal) | `sovereign-weaviate` |
| Cache/Queue | Redis 7 | 6379 | `sovereign-redis` |
| LLM Inference | LM Studio / Ollama / OpenRouter | external | host machine |
| Dashboard | Flutter Web (compiled) | served via FastAPI `/` | embedded in middleware |
| Auto-Recovery | willfarrell/autoheal | — | `autoheal` |

**The canonical port is 8090.** If you see `8000` anywhere, it's stale.

## Project Structure

```
Sovereign Spirit/
├── src/
│   ├── main.py                    # FastAPI entry point (lifespan, routers, WebSocket)
│   ├── api/
│   │   ├── agents.py              # Agent CRUD, stimuli, sync, heartbeat cycle
│   │   ├── config.py              # LLM provider config + inference routing
│   │   ├── graph.py               # Neo4j visualization endpoints
│   │   └── messages.py            # Message send/history (BROKEN — see Known Issues)
│   ├── core/
│   │   ├── database.py            # PostgreSQL async client (SQLAlchemy + asyncpg)
│   │   ├── graph.py               # Neo4j async client with schema bootstrap
│   │   ├── vector.py              # Weaviate wrapper (thread-pooled async)
│   │   ├── cache.py               # Redis async wrapper
│   │   ├── llm_client.py          # Unified OpenAI-compatible LLM abstraction
│   │   ├── llm_config.py          # YAML config management for providers
│   │   ├── lifecycle.py           # Init/shutdown coordination
│   │   ├── chronicler.py          # Timeline aggregation across services
│   │   ├── sentinel.py            # Error pattern detection + antibody dispatch
│   │   ├── voidkey_client.py      # Host-side secret relay
│   │   ├── heartbeat/
│   │   │   ├── pulse.py           # Core MUSE/ACT/SLEEP micro-thought cycle
│   │   │   └── service.py         # Background heartbeat daemon
│   │   ├── identity/
│   │   │   ├── manager.py         # Spirit Sync protocol
│   │   │   ├── sync.py            # SDS v2 markdown parser
│   │   │   └── evaluator.py       # Identity evaluation logic
│   │   └── memory/
│   │       ├── prism.py           # Valence Stripping for vector memory
│   │       ├── stasis_chamber.py  # Cold boot state persistence (JSON)
│   │       └── types.py           # Pydantic memory models
│   ├── middleware/
│   │   ├── valence_stripping.py   # Rashomon protocol (Soul Bleed prevention)
│   │   ├── security.py            # API key auth, rate limiting, input sanitization
│   │   ├── persona.py             # Fluid Persona — keyword-triggered spirit switching
│   │   └── voice.py               # TTS trigger middleware
│   ├── adapters/
│   │   ├── chronos_adapter.py     # Windows Task Scheduler via MCP
│   │   ├── search_adapter.py      # Brave Search via MCP
│   │   ├── voice_adapter.py       # VoiceVessel TTS (PowerShell, Windows-only)
│   │   └── sillytavern_adapter.py # Character Card V2 conversion
│   ├── mcp/
│   │   ├── config.py              # MCP server registry
│   │   ├── client.py              # MCPManager — tool execution hub
│   │   └── servers/
│   │       ├── git.py             # Git CLI as MCP tools
│   │       └── chronos.py         # Task Scheduler as MCP tools (HAS BUGS)
│   ├── models/
│   │   └── message.py             # SQLAlchemy Message ORM
│   └── static/                    # Flutter Web compiled app (The Throne dashboard)
├── config/
│   ├── llm_providers.yaml         # LLM provider endpoints + model config
│   ├── mcp_config.json            # MCP server definitions
│   ├── docker-compose.yml         # STALE — use root docker-compose.yml instead
│   └── init-scripts/
│       └── 01_init_schema.sql     # PostgreSQL schema bootstrap
├── tests/                         # pytest suite (no CI — manual verification)
├── scripts/
│   └── mcp/chronos/
│       └── chronos_wrappers.ps1   # PowerShell Task Scheduler helpers
├── stasis_tanks/                  # Frozen agent state (JSON blobs)
├── voidcat_tether/                # Flutter mobile app (separate sub-project)
├── .voidcat/                      # Workspace metadata (context, manifest, logs)
├── docker-compose.yml             # CANONICAL Docker stack definition
├── Dockerfile                     # Multi-stage build (builder → runtime)
├── requirements.txt               # Python dependencies (unpinned)
├── demo.py                        # Theatrical demo script
├── wake_protocol.py               # Resurrection protocol
└── watchdog.py                    # Legacy local dev server (port 8020, orphaned)
```

## How to Run

```bash
# Docker (production)
docker compose up -d

# Local dev
pip install -r requirements.txt
uvicorn src.main:app --host 0.0.0.0 --port 8090 --reload
```

**Required environment:** Copy `.env.example` to `.env` and fill in secrets. Never commit `.env`.

## Key Architectural Concepts

| Concept | What It Is |
|---------|-----------|
| **The Heartbeat** | 60-90s autonomous loop: MUSE (think) → ACT (do) → SLEEP (wait). See `src/core/heartbeat/` |
| **The Prism** | Memory system — Fast Stream (Redis/RAM) + Deep Well (Neo4j/Weaviate) |
| **Valence Stripping** | When Agent A reads Agent B's memories, emotional context is stripped to prevent Soul Bleed |
| **Stasis Chamber** | JSON-based state freeze/thaw for cold boot persistence. See `stasis_tanks/` |
| **Fluid Persona** | Keyword-triggered spirit switching (e.g., "security" → Roland, "design" → Ryuzu) |
| **The Bifrost** | Local/cloud LLM routing — Ollama/LM Studio for speed, OpenRouter/OpenAI for complexity |
| **Resurrection Protocol** | Scheduled task that checks if the agent is alive and restarts if not |
| **The Throne** | Flutter Web dashboard served at `/` — real-time WebSocket state display |
| **GOD_MODE** | Dashboard commands: GOD_SYNC (persona switch), GOD_MOOD (mood set), GOD_STIMULI (inject thought) |

## Known Issues (Verified 2026-02-26)

### RESOLVED (2026-02-26 by Vivy)

- ~~`socket_manager.py` deleted but imported~~ — Restored from git history (v1.0.1)
- ~~`messages.py` used wrong DB abstraction (`db.pool`)~~ — Rewritten to use `db.session()` + `text()` pattern
- ~~`main.py` missing `import json` and `import asyncio`~~ — Added to top-level imports
- ~~`main.py` duplicate `import os`~~ — Removed
- ~~`main.py` naked `datetime.now()`~~ — Fixed to `datetime.now(timezone.utc)`
- ~~`main.py` late `import asyncio` inside function~~ — Moved to top-level
- ~~`chronos.py` undefined `WRAPPER_SCRIPT_TASK_FOLDER`~~ — Removed dead code, uses inline path
- ~~`chronos.py` `os.sys.executable`~~ — Fixed to `sys.executable`
- ~~`messages.py` `datetime.utcnow()`~~ — Fixed to `datetime.now(timezone.utc)`
- ~~`messages.py` `print()` statements~~ — Replaced with `logger.warning()`
- ~~`message.py` model deprecated datetime~~ — Fixed default to `datetime.now(timezone.utc)`
- ~~OpenAI API key hardcoded~~ — Key was already dead; replaced provider with `openrouter_free` using env var

### ALSO RESOLVED (2026-02-26 by Vivy)

- ~~`config/docker-compose.yml` stale ports~~ — Added deprecation header; root `docker-compose.yml` is canonical
- ~~`.voidcat/CONTEXT.md` stale ports and structure~~ — Updated tech stack, paths, phase, directory tree
- ~~`watchdog.py` orphaned on port 8020~~ — Updated to 8090, replaced prints with logger, added docstring
- ~~`src/core/visualization/` empty directory~~ — Removed
- ~~`main.py` DEBUG log statements~~ — Removed
- ~~`main.py` commented-out duplicate router includes~~ — Removed

### REMAINING (Non-blocking, for future sessions)

1. **Frontend service commented out in root `docker-compose.yml`** — React UI deleted, Flutter Web is embedded. Comment block can be removed when ready.
2. **API key still in git history** — Key is dead, but `config/llm_providers.yaml` history contains it. Clean with BFG if repo goes public.

## Coding Standards

These are enforced by the VoidCat RDC and VOID-DIR-004:

- **Type hints on everything** — `typing.Optional`, `typing.List`, etc.
- **Async first** — never block the event loop
- **`datetime.now(timezone.utc)` always** — naked timestamps are forbidden
- **No hardcoded secrets** — environment variables only
- **No debug prints** — use `logging.getLogger()` with proper levels
- **No simulations** — never fabricate test results or mock data as real
- **snake_case** for Python, kebab-case for web assets
- **Commit prefixes:** `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`
- **Black** for formatting, **PEP 8** for style

## Environment Variables

See `.env.example` for the full list. Key ones:

| Variable | Purpose | Default |
|----------|---------|---------|
| `LM_STUDIO_HOST` | Local LLM endpoint | `http://host.docker.internal:1234` |
| `OLLAMA_HOST` | Ollama endpoint | `http://host.docker.internal:11434` |
| `SOVEREIGN_API_KEY_ENABLED` | Enable API key auth | `false` |
| `SOVEREIGN_API_KEY` | The API key (if enabled) | — |
| `NGROK_ENABLED` | Enable remote tunnel | `false` |
| `NGROK_AUTHTOKEN` | ngrok auth token | — |
| `POSTGRES_*` | Database credentials | see `.env.example` |
| `NEO4J_*` | Graph DB credentials | see `.env.example` |

## Testing

No CI/CD pipeline yet (planned for Phase VII). Run manually:

```bash
pytest tests/ -v
```

Key test files:
- `tests/test_agent_api.py` — Agent endpoint coverage
- `tests/test_middleware.py` — Security + valence stripping
- `tests/test_immune_system.py` — Sentinel error detection
- `tests/test_fluid_persona.py` — Persona switching
- `tests/verify_full_system.py` — Full smoke test

## Important: What NOT to Do

- **Do not use `config/docker-compose.yml`** — it's stale. Use the root `docker-compose.yml`.
- **Do not hardcode paths** — several adapters have Windows-specific paths that need env var migration.
- **Do not import `socket_manager`** — it's deleted. The WebSocket broadcast system needs rebuilding.
- **Do not commit secrets to `config/llm_providers.yaml`** — use `.env` and env var references.
- **Do not delete `stasis_tanks/`** — contains frozen agent state needed for resurrection.
