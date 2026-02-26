# Throne Dashboard — NOC Redesign
**Date:** 2026-02-26
**Status:** Approved
**Author:** Vivy (Context Integrator)

---

## Goal

Replace the current single-agent Throne view with a proper operator NOC layout: three agent panels visible simultaneously, a persistent GOD MODE console, a collapsed aggregate log feed, and a fully functional Memory tab (Prism + Stasis Chamber).

---

## Layout

```
┌────┬──────────────────────────────────────────────────────────┐
│    │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│ V  │  │   RYUZU      │  │   ALBEDO     │  │   BEATRICE   │  │
│    │  │  [status]    │  │  [status]    │  │  [status]    │  │
│ T  │  │  [last pulse]│  │  [last pulse]│  │  [last pulse]│  │
│    │  │  [SYNC] [⚡] │  │  [SYNC] [⚡] │  │  [SYNC] [⚡] │  │
│ M  │  └──────────────┘  └──────────────┘  └──────────────┘  │
│    ├─────────────────────────────────────────────────────────┤
│    │  SYSTEM LOGS (30%)             │  GOD MODE (70%)        │
└────┴──────────────────────────────────────────────────────────┘
```

- **Navigation rail** (far left): V icon, Throne, Memory
- **Agent grid** fills top ~60% — three equal columns, no scrolling
- **Bottom bar** fixed height ~280px — collapsed logs left, console right
- Mobile (<900px): unchanged — routes to ChatScreen

Expanding to N agents later: swap `Row` for `GridView(crossAxisCount: 3)`.

---

## Agent Card

```
┌─────────────────────────────────┐
│ ● RYUZU  · Iron Maid            │
│   Mood: Vigilant                │
│   Uptime: 2860341s              │
├─────────────────────────────────┤
│ 09:04:17  ACT                   │
│ "Scanning for directives..."    │
├─────────────────────────────────┤
│  [SYNC]        [FORCE PULSE]    │
└─────────────────────────────────┘
```

**Three zones:**

1. **Status zone** — spirit name + designation, status dot, mood badge, uptime counter
2. **Last pulse zone** — timestamp, action type label, thought text (2 lines max, truncated). Shows "Waiting for first pulse..." until heartbeat fires
3. **Action zone** — SYNC (sends `GOD_SYNC` with agent pre-filled), FORCE PULSE (sends `GOD_STIMULI` targeted at this agent)

**Status dot logic:**
- Green — heartbeat received within last 2 minutes
- Amber — stale (>2 min since last heartbeat)
- Red — no data received

**Mood badge:** colored pill — Neutral (gray), Vigilant (amber), Focused (blue), Synchronized (teal)

---

## Bottom Bar

```
┌──────────────────────────┬────────────────────────────────────┐
│ SYSTEM LOGS  [LIVE]      │ GOD MODE                           │
│ 09:04  RYUZU  ACT        │  VoidCat Sovereign Spirit v1.0.0   │
│ 09:03  ALBEDO MUSE       │  > System initialized.             │
│ 09:02  BEAT.  SLEEP      │  > GOD_SYNC → Ryuzu: processed     │
│ [+47 more]               │  ─────────────────────────────     │
│                          │  > Enter command...                │
└──────────────────────────┴────────────────────────────────────┘
```

- **SYSTEM LOGS (flex: 3)** — last 3 events across all agents (agent name, action, time), `[+N more]` count. Display-only; no expand in this scope
- **GOD MODE (flex: 7)** — existing console, echoes which agent a command targeted. Output scrolls up, input docked at bottom
- Layout: `Row` with `Expanded(flex: 3)` and `Expanded(flex: 7)`

---

## Memory Tab

```
┌────┬──────────────────────────────┬───────────────────────────┐
│    │  THE PRISM                   │  STASIS CHAMBER           │
│    │  [Agent ▾] [Type ▾] [Search] │  ryuzu.ptr    2026-02-26  │
│    │  ─────────────────────────── │  [RESTORE]                │
│    │  Fast Stream (12)            │  ─────────────────────────│
│    │  > Memory about Wykeve...    │  albedo.ptr   2026-02-25  │
│    │  > System boot at 09:00...   │  [RESTORE]                │
│    │  Deep Well (3)               │  ─────────────────────────│
│    │  > [Neo4j node]              │  beatrice.ptr 2026-02-24  │
│    └──────────────────────────────┴───────────────────────────┘
```

**Left — The Prism:**
- Agent dropdown, type filter (Fast Stream / Deep Well), search input
- Results as cards: content preview + timestamp
- Pulls from existing `/api/memory/` endpoints
- Read-only

**Right — Stasis Chamber:**
- Lists `.ptr` files from `stasis_tanks/` with timestamps
- RESTORE button → `POST /api/stasis/{agent_id}/restore`
- No content preview — file metadata only
- Read-only

Both panels are read-only in this scope. No create/delete.

---

## Backend Contract Changes

The WebSocket `STATE_UPDATE` payload must be expanded from single-agent to multi-agent:

**Current:**
```json
{
  "type": "STATE_UPDATE",
  "payload": {
    "identity": { "name": "Albedo", "persona": "..." },
    "mind": { "mood": "Neutral", "current_goal": "..." },
    "stats": { "uptime": 2860341 }
  }
}
```

**New:**
```json
{
  "type": "STATE_UPDATE",
  "payload": {
    "agents": [
      {
        "id": "ryuzu",
        "name": "Ryuzu",
        "designation": "Iron Maid",
        "mood": "Vigilant",
        "last_pulse": {
          "timestamp": "2026-02-26T09:04:17Z",
          "action": "ACT",
          "thought": "Scanning for directives..."
        },
        "uptime": 2860341
      },
      { "id": "albedo", ... },
      { "id": "beatrice", ... }
    ]
  }
}
```

The Flutter `dashboardStateProvider` fans this array out to each agent card by ID.

**New endpoints required:**
- `GET /api/memory/?agent_id=&type=&search=` — Prism viewer
- `GET /api/stasis/` — list stasis snapshots
- `POST /api/stasis/{agent_id}/restore` — restore a snapshot

---

## Out of Scope

- Memory create/delete
- Expand-on-click for SYSTEM LOGS
- Mobile Throne view (stays as ChatScreen)
- Agent count >3 (GridView refactor deferred)
- Offline/cached state

---

## Files Affected

**Flutter (`voidcat_tether/lib/`):**
- `features/dashboard/dashboard_screen.dart` — refactor `_ThroneView` to 3-column grid + new bottom bar
- `features/dashboard/widgets/agent_card.dart` — NEW: three-zone agent card widget
- `features/dashboard/widgets/log_stream_widget.dart` — update to consume multi-agent payload
- `features/dashboard/widgets/console_widget.dart` — update echo format
- `features/memory/memory_screen.dart` — NEW: Prism + Stasis layout
- `features/memory/widgets/prism_panel.dart` — NEW
- `features/memory/widgets/stasis_panel.dart` — NEW
- `services/websocket_service.dart` — update stream to handle new payload shape

**Backend (`src/`):**
- `src/main.py` — expand `STATE_UPDATE` to multi-agent array
- `src/api/memory.py` — NEW: Prism query endpoint
- `src/api/stasis.py` — NEW: stasis list + restore endpoints
