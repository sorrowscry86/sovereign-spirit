# Throne Control Panels — Bifrost & Tools Upgrade + Ryuzu Consolidation
**Date:** 2026-03-05
**Author:** Vivy (Context Integrator)
**Status:** Approved

---

## Objective

Upgrade the Bifrost and Tools tabs in the Throne dashboard from read-only viewers to interactive control panels. Consolidate the Ryuzu/Ryuzu Meyer spirit duplication.

---

## 1. Bifrost Panel — LLM Connection Management

### Mode Switcher (existing, behavior change)

The LOCAL / AUTO / CLOUD toggle stays. Behavioral definitions:

| Mode | Behavior |
|------|----------|
| **LOCAL** | Force all inference to local providers only. No cloud calls. |
| **AUTO** | Cloud-first, local fallback. On cloud failure: route to local, log failure visibly. On cloud recovery: route back up. On startup: auto-warm LM Studio with `qwen3-4b-thinking`. |
| **CLOUD** | Force all inference to cloud providers only. No local calls. |

### AUTO Self-Healing Logic

On startup (or when AUTO mode is set):
1. Hit LM Studio `/v1/models` to check if a model is loaded.
2. If not loaded or LM Studio unreachable, attempt to load `qwen3-4b-thinking` via LM Studio API.
3. Health check confirms local is ready.
4. Log: "Local fallback warmed up."

Cloud failure behavior:
- When cloud provider returns error/timeout → fall to next in fallback chain.
- Amber banner appears in Bifrost panel: `"⚠ Cloud unavailable — routed to [local]. [timestamp]"`.
- Banner persists until cloud recovers or user dismisses.
- Failure event logged to system logs with timestamp and error detail.

### Provider Cards (interactive upgrade)

Each provider card expands on tap to show editable configuration:

**Dropdowns:**
- Provider type: Ollama, LM Studio, OpenRouter, OpenAI
- Model: populated per provider type (free text fallback for custom models)

**Text fields:**
- Endpoint URL
- API key (masked, reveal toggle)
- Max tokens
- Temperature
- Timeout

**Actions per card:**
- **Health light** — green/red dot, auto-refresh every 30s (existing)
- **Test Connection** — pings provider health endpoint, shows pass/fail inline
- **Test Reply** — sends "Say hello in one sentence", shows actual LLM response inline
- **Save** — persists changes to `llm_providers.yaml` via `POST /config/llm`

### Fallback Chain

- Reorderable list showing provider priority order (drag handles).
- Active primary provider is the top entry.
- Save writes `active_provider` and `fallback_chain` to YAML.

### Backend Additions

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/config/llm/health/{name}` | Single provider health check |
| POST | `/config/llm/test/{name}` | Send test prompt, return LLM response |
| POST | `/config/llm/warm` | Trigger LM Studio model load for AUTO warm-up |

Existing endpoints unchanged:
- `GET /config/inference` — returns mode + current route
- `POST /config/inference` — update mode
- `GET /config/llm` — full provider config (keys masked)
- `POST /config/llm` — save provider config
- `GET /config/llm/health` — all providers health

---

## 2. Tools Panel — MCP Tool Management

### Server Cards (interactive upgrade)

Each server group keeps its expandable layout with:
- **Connection light** — green/red (existing)
- **Test** button — reconnects server, re-lists tools, confirms alive
- **Disconnect** button — kills server session cleanly

### Add Server

Button at top: `"+ Add MCP Server"`
- Dropdown for type: `filesystem`, `git`, `chronos`, `search`, `custom`
- Known types pre-fill command/args from registry defaults
- Custom type: text fields for command + args (space-separated)
- Save writes to MCP registry and connects immediately

### Tool Testing

Each tool tile gets a "play" icon:
- Tap → shows input schema as auto-generated form (from JSON schema)
- Fill params, hit "Run" → executes tool, shows raw result inline
- Diagnostic use: verify tools actually work

### Backend Additions

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/config/tools/connect/{server_name}` | Connect/reconnect an MCP server |
| POST | `/config/tools/disconnect/{server_name}` | Disconnect an MCP server |
| POST | `/config/tools/test/{server_name}/{tool_name}` | Execute tool with args, return result |
| GET | `/config/tools/registry` | Return raw MCP_SERVER_REGISTRY |
| POST | `/config/tools/registry` | Add/update a server entry |

---

## 3. Ryuzu Consolidation

### Problem

"Ryuzu" and "Ryuzu Meyer" exist as two separate agent rows in the database. All code references use "Ryuzu". The duplicate causes confusion in the agent grid.

### Solution

1. **Merge personality** — read both agent records, combine traits/designation into a single coherent Ryuzu identity.
2. **DB migration** — SQL script that:
   - Updates `Ryuzu` row with merged personality fields
   - Reassigns any foreign keys (tether_messages, tether_participants, projects) from Ryuzu Meyer's UUID to Ryuzu's UUID
   - Deletes the Ryuzu Meyer row
3. **Evaluator roster** — already correct (only lists "Ryuzu")
4. **Persona middleware** — already correct (maps to "Ryuzu")

---

## Invariants Preserved

- **Security** — all new endpoints inherit `X-API-Key` middleware. Tool execution requires auth.
- **No secrets in responses** — API keys remain masked in GET responses. Only `POST /config/llm` accepts real keys.
- **Singleton discipline** — all new methods on existing `LLMClient`, `MCPManager`. No new singletons.
- **YAML as source of truth** — provider config persists to `llm_providers.yaml`. MCP registry updates persist to `mcp/config.py` registry dict (runtime only for now; YAML persistence is a future enhancement).

---

## Out of Scope

- Adding/removing LLM providers from UI (edit existing only; add via YAML)
- MCP registry YAML persistence (runtime-only for this iteration)
- LM Studio model download (assumes model already available locally)
- Prometheus metrics for failure events (FUTURE-004)
