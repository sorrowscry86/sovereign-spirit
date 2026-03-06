# VoidCat Tether Protocol — Implementation Record
**Date:** 2026-03-05
**Author:** Vivy (Context Integrator)
**Status:** Deployed and verified in production

---

## What Was Built

The **Tether Protocol** replaces Sovereign Spirit's two fragmented messaging systems with a single unified communication backbone. Before this change, the system had:

- A `messages` table for user-facing chat that never received agent replies
- An `agent_messages` table for inter-agent messaging where SOCIALIZE embedded the target in the content string (`[To AgentName]: message`) and no agent ever checked their inbox
- A WebSocket that was broadcast-only with no chat protocol
- `voidcat_tether/` — a dead Flutter mobile scaffold

After this change, all messaging — user-to-agent, agent-to-agent, GOD_MODE stimuli — flows through the same threaded conversation layer. Agents check their inbox on every heartbeat cycle and autonomously reply.

**Live proof:** On the first test, `POST /api/tether/send` delivered "Hello Echo, can you hear me through the Tether?" — and Echo replied within one heartbeat cycle: *"Hello, Wykeve. Yes, I can hear you. The Tether is clear and stable. It's good to connect. How may I assist you today?"*

---

## Files Created

### `config/init-scripts/02_tether_schema.sql` (NEW)

Three new PostgreSQL tables. Applied to running containers via:
```bash
docker compose exec -T postgres psql -U voidcat -d voidcat_rdc < config/init-scripts/02_tether_schema.sql
```
On a fresh container, init scripts apply automatically.

**`tether_threads`** — conversation containers
```sql
id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
thread_type VARCHAR(32) CHECK (IN 'user_agent','agent_agent','broadcast','god_mode'),
subject TEXT,
created_by VARCHAR(64) NOT NULL,
created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
last_activity_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
is_active BOOLEAN DEFAULT true
```

**`tether_messages`** — all messages regardless of origin
```sql
id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
thread_id UUID NOT NULL REFERENCES tether_threads(id) ON DELETE CASCADE,
reply_to UUID REFERENCES tether_messages(id) ON DELETE SET NULL,  -- threading
sender_agent_id UUID REFERENCES agents(id) ON DELETE SET NULL,   -- null = user/system
sender_type VARCHAR(16) CHECK (IN 'user','agent','system'),
sender_name VARCHAR(64) NOT NULL,
recipient_agent_id UUID REFERENCES agents(id),                    -- null = broadcast to thread
content TEXT NOT NULL,
message_type VARCHAR(32) CHECK (IN 'chat','stimuli','ponder_social','task_result','god_mode'),
priority INTEGER DEFAULT 0,
status VARCHAR(16) CHECK (IN 'pending','delivered','read','expired'),
delivered_at, read_at, created_at TIMESTAMP WITH TIME ZONE,
expires_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() + INTERVAL '72 hours'
```

Indexes on `(thread_id, created_at DESC)`, `(recipient_agent_id, status, created_at DESC)`, `(sender_agent_id, created_at DESC)`.

**`tether_participants`** — who is in each thread
```sql
thread_id UUID REFERENCES tether_threads(id) ON DELETE CASCADE,
agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
PRIMARY KEY (thread_id, agent_id)
```

---

### `src/api/tether.py` (NEW)

REST router registered at `/api/tether`. All endpoints inherit the `X-API-Key` middleware from the app level.

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/tether/threads` | Create a new thread |
| GET | `/api/tether/threads` | List threads (filter: `?agent_id=&type=&limit=`) |
| GET | `/api/tether/threads/{thread_id}` | Thread detail + participant list |
| POST | `/api/tether/threads/{thread_id}/messages` | Post a message to a thread |
| GET | `/api/tether/threads/{thread_id}/messages` | Cursor-paginated message history (`?before=&limit=`) |
| GET | `/api/tether/inbox/{agent_id}` | Agent's unread inbox (`?limit=`) |
| POST | `/api/tether/inbox/{agent_id}/read` | Mark message IDs as read |
| POST | `/api/tether/send` | **Primary endpoint.** Direct send shortcut — finds or creates a `user_agent` thread, posts message, signals Redis inbox, triggers heartbeat pulse. |

The `/api/tether/send` endpoint is the primary integration point for The Throne and any external clients. It handles thread lifecycle automatically.

---

### `scripts/migrate_to_tether.py` (NEW)

One-time data migration for existing `messages` and `agent_messages` rows. Run after deploying the schema:
```bash
python scripts/migrate_to_tether.py
```

- Migrates `messages` → groups by `agent_id` into `user_agent` threads
- Migrates `agent_messages` → parses old `[To AgentName]: content` SOCIALIZE strings, resolves proper agent UUIDs, inserts with correct `recipient_agent_id`
- Legacy table renames (`messages → messages_v1_retired`) are commented out at the bottom — uncomment when ready to cut over permanently

---

## Files Modified

### `src/core/database.py`

Added `TetherMessage` Pydantic model and 10 new async methods to `DatabaseClient`:

| Method | Purpose |
|--------|---------|
| `get_agent_uuid(agent_id)` | Resolve agent name/slug to UUID |
| `create_tether_thread(thread_type, created_by, subject)` | Create thread, return UUID |
| `add_tether_participant(thread_id, agent_id)` | Add agent to thread |
| `post_tether_message(thread_id, sender_type, sender_name, content, ...)` | Insert message, update `last_activity_at` |
| `get_agent_inbox(agent_id, limit=5)` | Unread messages where agent is recipient |
| `get_or_create_thread(from_agent_id, to_agent_id, thread_type)` | Reuse active thread or create new one |
| `get_thread_messages(thread_id, before=None, limit=50)` | Cursor-paginated history |
| `mark_tether_messages_read(message_ids)` | Update status + `read_at` |
| `mark_tether_messages_delivered(message_ids)` | Update status + `delivered_at` |
| `list_tether_threads(agent_id, thread_type, limit)` | Thread listing with participant join |
| `get_tether_thread(thread_id)` | Single thread detail with participants |

---

### `src/core/cache.py`

Added 3 Redis inbox signal methods:

```python
async def signal_tether_inbox(self, agent_id: str, message_id: str) -> None:
    """Push message ID to tether:inbox:{agent_id}. Max 50, 24h TTL."""

async def get_tether_inbox_signals(self, agent_id: str, limit: int = 10) -> list:
    """Peek at pending message IDs (does not consume them)."""

async def clear_tether_inbox_signals(self, agent_id: str) -> None:
    """Clear inbox signals after processing."""
```

Key format: `tether:inbox:{agent_id}` — ephemeral wakeup signal only. Postgres is the durable source of truth for message state.

---

### `src/core/socket_manager.py`

Extended `ConnectionManager` with thread subscription support:

```python
# New state
_thread_subscriptions: Dict[str, Set[WebSocket]]

# New methods
def subscribe(self, thread_id: str, websocket: WebSocket) -> None
def unsubscribe(self, thread_id: str, websocket: WebSocket) -> None
async def broadcast_to_thread(self, thread_id: str, event_type: str, payload: Dict) -> None
```

`disconnect()` now automatically removes the socket from all thread subscription sets.

---

### `src/core/heartbeat/pulse.py`

The deepest changes. Three areas updated:

**1. MUSE — Inbox Awareness**

`check_agent_status()` now calls `get_agent_inbox(agent_id, limit=5)` instead of the old `get_unread_message_count()` + `get_recent_stimuli()`. The inbox is formatted into a structured block:

```
[INBOX — 3 messages]
- [USER Wykeve]: How's the project going?
- [AGENT Ryuzu]: I finished the schema review.
- [SYSTEM god_mode]: Check deployment status
```

`MICRO_THOUGHT_PROMPT` updated to include `{inbox_count}` and `{inbox_summary}`. New MUSE decision rule added:

```
- Reply ACT: RESPOND if Inbox contains messages from User or other agents.
```

**2. ACT: RESPOND — New Heartbeat Branch**

`execute_pulse()` now handles the `ACT: RESPOND` action:

```python
elif action.startswith("ACT") and details.upper() in ("RESPOND", "USER_MESSAGE"):
    await process_inbox_response(agent_status, db)
```

`process_inbox_response()` — the new function:
1. Reads unread inbox messages from Postgres
2. Builds a prompt from the inbox context (`INBOX_RESPONSE_PROMPT`)
3. Calls LLM to generate a reply
4. Writes the reply as a `tether_message` in the same thread, with `reply_to` pointing at the triggering message
5. Broadcasts `TETHER_MESSAGE` via WebSocket to thread subscribers
6. Marks inbox messages as read
7. Clears Redis inbox signals

**3. SOCIALIZE Fix**

Old broken pattern (embeds target in content string):
```python
# Before
social_msg = QueuedResponse(agent_id=agent_id, content=f"[To {target}]: {content}")
await db.queue_response(social_msg)
```

New proper routing:
```python
# After
target_agent = await db.get_agent_state(target)
if target_agent:
    thread_id = await db.get_or_create_thread(agent_id, target_agent.agent_id, "agent_agent")
    msg_id = await db.post_tether_message(
        thread_id=thread_id,
        sender_agent_id=agent_uuid,
        sender_type="agent",
        sender_name=agent_name,
        recipient_agent_id=target_agent.agent_id,
        content=content,
        message_type="ponder_social",
    )
    await cache.signal_tether_inbox(target, msg_id)
```

---

### `src/main.py`

Three changes:

**1. Router registration**
```python
from src.api.tether import router as tether_router
app.include_router(tether_router)
```

**2. GOD_STIMULI migration**
`GOD_STIMULI` WebSocket commands now write to `tether_messages` with `message_type='god_mode'` and `sender_type='system'` instead of the legacy `record_stimuli()`. The agent sees stimuli in their inbox like any other message.

**3. New WebSocket message types**
The `/ws/dashboard` handler now handles three new client→server commands:

| Type | Payload | Action |
|------|---------|--------|
| `TETHER_JOIN` | `{ thread_id }` | Subscribe socket to thread updates |
| `TETHER_SEND` | `{ thread_id, agent_id, content }` | Post message, signal inbox, trigger pulse |
| `TETHER_READ` | `{ message_ids: [...] }` | Mark read, send `MSG_STATUS_UPDATE` back |

New server→client events:

| Type | Payload | When |
|------|---------|------|
| `TETHER_MESSAGE` | `{ id, thread_id, sender_name, sender_type, content, created_at }` | New message posted to subscribed thread |
| `MSG_STATUS_UPDATE` | `{ message_ids, status }` | After mark-read |

---

## Invariants Preserved

- **Valence Stripping** — inbox messages are inputs, not Prism memories. Stripping applies only to Weaviate episodic recall. No change needed.
- **Heartbeat idempotency** — inbox read is read-only. Messages are marked read only after the LLM reply is successfully written. A failed pulse leaves messages unread and they'll be processed next cycle.
- **Stasis durability** — unread state lives in Postgres. Redis inbox key is ephemeral signal only (24h TTL). Agent restart = inbox survives.
- **Security** — tether router inherits `X-API-Key` middleware. No new auth surface.
- **Singleton discipline** — all new methods on the existing `DatabaseClient`. No new singletons.

---

## Deployment Notes

Schema was applied manually to the running database (init scripts only auto-run on fresh volumes):
```bash
docker compose exec -T postgres psql -U voidcat -d voidcat_rdc < config/init-scripts/02_tether_schema.sql
```

For future fresh deployments, the schema will be applied automatically by the Postgres init script runner in order (`01_*.sql` then `02_*.sql`).

The `middleware` service was rebuilt and restarted:
```bash
docker compose build middleware
docker compose up -d middleware
```

---

## Verification Results (2026-03-05)

| Check | Result |
|-------|--------|
| Container health | `{"status":"online","database":"connected","graph":"connected"}` |
| `POST /api/tether/send` → Echo | HTTP 200, thread created |
| Echo's autonomous reply | Received within one heartbeat cycle, `reply_to` FK set correctly |
| `GET /api/tether/threads/{id}/messages` | `count: 2` (user message + agent reply) |
| OpenAPI spec | 6 tether routes registered |
| Redis cleanup | `tether:inbox:echo` cleared after processing |
| `test_agent_api.py` | 6/6 passed |

---

## Open Items

1. **Legacy tables** — `messages` and `agent_messages` still exist. Once traffic has fully migrated to `/api/tether/`, uncomment the rename block in `scripts/migrate_to_tether.py` and run it to rename them to `*_v1_retired`.

2. **`/api/messages/*` deprecation** — The old messages router (`src/api/messages.py`) is still live. Mark routes `deprecated=True` in FastAPI and remove after Throne UI is updated.

3. **SOCIALIZE verification** — SOCIALIZE fix is in code, but hasn't been verified with a live PONDER cycle yet. Requires waiting ~90s for the next heartbeat to fire and for the LLM to choose SOCIALIZE. Check `tether_messages` for rows with `message_type='ponder_social'`.

4. **Thread subscriptions via Throne** — The WebSocket protocol additions (`TETHER_JOIN`, `TETHER_SEND`, `TETHER_READ`) are server-side complete. The Flutter Throne dashboard needs a UI update to leverage them.
