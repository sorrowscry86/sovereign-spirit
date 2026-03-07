# Tool Lifecycle + Reply Chain Implementation Plan (2026-03-06)

## Objective

Implement a coherent WebSocket-driven tool lifecycle pipeline with approval gating, reply-chain tracking, and auditable event persistence.

## Directive Alignment

1. Add TTL for `waiting_approval` (default `300` seconds), auto-deny on expiry, and release the thread/chain.
2. Add MCP registry `security_tier` to support `deny_sensitive_only` policy mode.
3. Couple `process_inbox_response` with `REPLY_CHAIN_EVENT` transitions and inject tool outputs into active LLM context before next turn.

## Contract

### WebSocket Events

- `TOOL_USE_EVENT`
- `TOOL_USE_APPROVAL_REQUIRED`
- `REPLY_CHAIN_EVENT`
- `CMD_ACK`

### WebSocket Commands

- `TOOL_USE_APPROVE`
- `TOOL_USE_DENY`
- `REPLY_CHAIN_RESUME`
- `REPLY_CHAIN_CANCEL`

### Tool Lifecycle Phases

- `requested`
- `executing`
- `completed`
- `failed`

### Reply Chain States

- `queued`
- `running`
- `waiting_tool`
- `waiting_approval`
- `completed`
- `failed`
- `cancelled`

## Data Model Additions

### Runtime Configuration

- `TOOL_APPROVAL_MODE`: `auto | ask | deny_sensitive_only` (default `auto`)
- `TOOL_APPROVAL_TTL_SECONDS`: integer seconds (default `300`)
- `TOOL_SENSITIVE_TIER_MIN`: integer threshold for sensitive-only mode (default `2`)

### MCP Registry

- `security_tier` integer on each server entry.

### Audit Persistence

Create runtime table `tool_execution_events` (idempotent create on startup) with:

- `event_id`
- `agent_id`
- `thread_id`
- `chain_id`
- `chain_step`
- `chain_status`
- `phase`
- `tool_name`
- `tool_server`
- `args_preview`
- `result_preview`
- `duration_ms`
- `timestamp`

## Implementation Sequence

1. Backend core scaffolding in `pulse.py`:
   - Event emitters for tool and chain events.
   - Approval gate with TTL polling against Redis.
   - Security-tier-aware gate decision.
2. Registry update in `src/mcp/config.py` and `/config/tools/registry` API:
   - Include and expose `security_tier`.
3. Dashboard command handling in `main.py`:
   - Accept approve/deny/resume/cancel commands.
   - Persist command decision in Redis and return `CMD_ACK`.
4. DB audit persistence in `database.py`:
   - Ensure runtime table exists.
   - Add event insert function.
5. Integrate `process_inbox_response` chain transitions end-to-end.

## Validation Matrix

1. `auto`: no pause, full lifecycle events emitted.
2. `ask`: pause at approval, resume after `TOOL_USE_APPROVE`.
3. `deny_sensitive_only`: sensitive tools blocked or paused based on policy.
4. TTL expiry: unresolved approvals become deny with clear failure event.
5. Multi-turn continuity: chain events map to a single `chain_id` across tool + reply phases.

## Notes

- Frontend Dart source is not currently visible in this workspace snapshot; backend event contract will be implemented first so UI can bind cleanly once source path is available.
