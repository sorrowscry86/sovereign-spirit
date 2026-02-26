# Throne NOC Dashboard Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rebuild the Throne dashboard into a 3-agent NOC layout with per-agent cards, an inline GOD MODE console, a collapsed log feed, and a functional Memory tab (Prism + Stasis Chamber).

**Architecture:** Backend WebSocket expands `STATE_UPDATE` to broadcast all agents as an array. Flutter fans this out to three `AgentCard` widgets displayed in a row. A new `MemoryScreen` replaces the placeholder, calling two new REST endpoints for Prism memory queries and Stasis snapshot management.

**Tech Stack:** Python/FastAPI (backend), Dart/Flutter (frontend), Riverpod (state), WebSocketChannel (real-time), flutter_riverpod StreamProvider (data flow)

---

## Reference Files

Before starting, read these:
- `src/main.py` — websocket_dashboard function (lines 345-470)
- `voidcat_tether/lib/features/dashboard/dashboard_screen.dart`
- `voidcat_tether/lib/services/websocket_service.dart`
- `voidcat_tether/lib/features/dashboard/widgets/log_stream_widget.dart`
- `voidcat_tether/lib/features/dashboard/widgets/console_widget.dart`
- `src/core/memory/stasis_chamber.py`
- `src/core/memory/prism.py`
- `src/core/database.py` (for `list_agents()`)
- `config/init-scripts/01_init_schema.sql` (column types for agents table)

---

## Task 1: Backend — Fix Late Import + Expand STATE_UPDATE to Multi-Agent

**Files:**
- Modify: `src/main.py`
- Test: run with `python -c "from src.main import app; print('OK')"`

**Context:** The `websocket_dashboard` function currently:
1. Has a late `from src.core.database import StimuliRecord` inside the handler (drift violation)
2. Sends a single-agent payload — `{"payload": {"identity": {...}, "mind": {...}, "stats": {...}}}`

We need it to send all agents as an array: `{"payload": {"agents": [...]}}`.

**Step 1: Move the late import to the top of main.py**

Find this line in `websocket_dashboard` (inside the `GOD_STIMULI` handler):
```python
from src.core.database import StimuliRecord
```

Remove it. Add `StimuliRecord` to the existing import at the top of main.py:
```python
from src.core.database import get_database, StimuliRecord
```

**Step 2: Replace both the initial state packet and the broadcast_updates() loop**

Find the `websocket_dashboard` function. Replace the initial state block and the `broadcast_updates` inner function with this:

```python
async def _build_all_agents_payload() -> dict:
    """Fetch all agents and build the multi-agent STATE_UPDATE payload."""
    agents = await db_client.list_agents()
    now = datetime.now(timezone.utc)
    agent_list = []
    for agent in agents:
        uptime = (now - agent.created_at).total_seconds() if agent.created_at else 0
        agent_list.append({
            "id": agent.name.lower(),
            "name": agent.name,
            "designation": agent.designation or "",
            "mood": agent.current_mood or "Neutral",
            "uptime": uptime,
            "last_pulse": None,  # populated by heartbeat broadcasts
        })
    return {"type": "STATE_UPDATE", "payload": {"agents": agent_list}}

# Send initial state
initial = await _build_all_agents_payload()
await websocket.send_json(initial)

async def broadcast_updates() -> None:
    """Broadcast all-agent state to the dashboard every 2 seconds."""
    try:
        while True:
            update = await _build_all_agents_payload()
            await websocket.send_json(update)
            await asyncio.sleep(2)
    except Exception as e:
        logger.debug(f"Broadcast loop stopped: {e}")
```

**Step 3: Verify compile**

```bash
cd "path/to/Sovereign Spirit"
python -m py_compile src/main.py && echo "CLEAN"
```
Expected: `CLEAN`

**Step 4: Rebuild container and verify WebSocket payload**

```bash
docker compose up middleware --build -d
sleep 4
python -c "
import asyncio, json, websockets
async def t():
    async with websockets.connect('ws://localhost:8090/ws/dashboard') as ws:
        msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
        agents = msg.get('payload', {}).get('agents', [])
        print(f'Agents received: {[a[\"name\"] for a in agents]}')
asyncio.run(t())
"
```
Expected: `Agents received: ['Ryuzu', 'Albedo', 'Beatrice']` (or whatever agents exist in DB)

**Step 5: Commit**

```bash
git add src/main.py
git commit -m "feat: expand STATE_UPDATE to multi-agent array in websocket broadcast"
```

---

## Task 2: Backend — Memory API Endpoint

**Files:**
- Create: `src/api/memory.py`
- Modify: `src/main.py` (register router)

**Context:** The Prism viewer in the Memory tab needs to query stored memories. Read `src/core/memory/prism.py` to understand what query methods exist before writing this endpoint. Use whatever method exists (likely `search_memories` or similar). If no suitable method exists, add a `list_memories(agent_id, limit)` method to the prism.

**Step 1: Create `src/api/memory.py`**

```python
"""
VoidCat RDC: Memory API
=======================
Endpoints for querying the Prism memory system.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from src.core.database import get_database
from src.core.memory.prism import get_prism
from src.middleware.security import verify_api_key

logger = logging.getLogger("sovereign.api.memory")

router = APIRouter(prefix="/api/memory", tags=["memory"])


@router.get("/")
async def list_memories(
    agent_id: Optional[str] = Query(None),
    memory_type: Optional[str] = Query(None, alias="type"),
    search: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    _: None = Depends(verify_api_key),
) -> dict:
    """
    List memories from the Prism.

    Filters by agent_id, type (fast_stream|deep_well), and optional search text.
    """
    try:
        prism = get_prism()
        # Read prism.py to find the correct method name.
        # Common patterns: prism.query(), prism.search(), prism.list()
        # Use whatever is available. Fall back to empty list if prism unavailable.
        memories = await prism.list_memories(
            agent_id=agent_id,
            memory_type=memory_type,
            search=search,
            limit=limit,
        )
        return {"memories": memories, "count": len(memories)}
    except Exception as e:
        logger.warning(f"Memory query failed: {e}")
        return {"memories": [], "count": 0, "error": str(e)}
```

**Step 2: Register the router in main.py**

Find the block where routers are included (look for `app.include_router`). Add:
```python
from src.api.memory import router as memory_router
# ...
app.include_router(memory_router)
```

**Step 3: Compile check**

```bash
python -m py_compile src/api/memory.py && echo "CLEAN"
```

**Step 4: Rebuild and smoke test**

```bash
docker compose up middleware --build -d && sleep 4
curl -s http://localhost:8090/api/memory/ | python -m json.tool
```
Expected: `{"memories": [...], "count": N}` — may be empty if no memories stored yet, but no 500 error.

**Step 5: Commit**

```bash
git add src/api/memory.py src/main.py
git commit -m "feat: add /api/memory/ endpoint for Prism viewer"
```

---

## Task 3: Backend — Stasis API Endpoints

**Files:**
- Create: `src/api/stasis.py`
- Modify: `src/main.py` (register router)

**Context:** The Stasis Chamber in the Memory tab needs to list `.ptr` files from `stasis_tanks/` and restore them. Read `src/core/memory/stasis_chamber.py` to understand the file format and restore method before writing this.

**Step 1: Create `src/api/stasis.py`**

```python
"""
VoidCat RDC: Stasis API
=======================
Endpoints for listing and restoring stasis chamber snapshots.
"""

import os
import logging
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from src.core.memory.stasis_chamber import StasisChamber
from src.middleware.security import verify_api_key

logger = logging.getLogger("sovereign.api.stasis")

router = APIRouter(prefix="/api/stasis", tags=["stasis"])

STASIS_DIR = os.getenv("STASIS_DIR", "stasis_tanks")


@router.get("/")
async def list_snapshots(_: None = Depends(verify_api_key)) -> dict:
    """List all stasis snapshot pointer files."""
    snapshots = []
    if os.path.isdir(STASIS_DIR):
        for fname in sorted(os.listdir(STASIS_DIR)):
            if fname.endswith(".ptr"):
                fpath = os.path.join(STASIS_DIR, fname)
                mtime = os.path.getmtime(fpath)
                snapshots.append({
                    "agent_id": fname.replace(".ptr", ""),
                    "filename": fname,
                    "modified": datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat(),
                })
    return {"snapshots": snapshots, "count": len(snapshots)}


@router.post("/{agent_id}/restore")
async def restore_snapshot(
    agent_id: str,
    _: None = Depends(verify_api_key),
) -> dict:
    """Restore an agent from its stasis snapshot."""
    try:
        chamber = StasisChamber(agent_id=agent_id, stasis_dir=STASIS_DIR)
        state = await chamber.restore()
        if state is None:
            raise HTTPException(status_code=404, detail=f"No snapshot found for {agent_id}")
        logger.info(f"Stasis restore: {agent_id}")
        return {"status": "restored", "agent_id": agent_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Stasis restore failed for {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

**Step 2: Register in main.py**

```python
from src.api.stasis import router as stasis_router
# ...
app.include_router(stasis_router)
```

**Step 3: Compile check**

```bash
python -m py_compile src/api/stasis.py && echo "CLEAN"
```

**Step 4: Rebuild and smoke test**

```bash
docker compose up middleware --build -d && sleep 4
curl -s http://localhost:8090/api/stasis/ | python -m json.tool
```
Expected: `{"snapshots": [...], "count": N}` with .ptr files from stasis_tanks/.

**Step 5: Commit**

```bash
git add src/api/stasis.py src/main.py
git commit -m "feat: add /api/stasis/ list and restore endpoints"
```

---

## Task 4: Flutter — AgentCard Widget

**Files:**
- Create: `voidcat_tether/lib/features/dashboard/widgets/agent_card.dart`
- Test: `voidcat_tether/test/agent_card_test.dart`

**Context:** This is the new per-agent panel replacing the three `StateMonitorCard` widgets. It receives a single agent's data map and renders the three-zone layout (status, last pulse, actions).

**Step 1: Write the failing test**

Create `voidcat_tether/test/agent_card_test.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:voidcat_tether/features/dashboard/widgets/agent_card.dart';

void main() {
  final testAgent = {
    'id': 'ryuzu',
    'name': 'Ryuzu',
    'designation': 'Iron Maid',
    'mood': 'Vigilant',
    'uptime': 3600.0,
    'last_pulse': {
      'timestamp': '2026-02-26T09:04:17Z',
      'action': 'ACT',
      'thought': 'Scanning for directives...',
    },
  };

  testWidgets('AgentCard renders agent name', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        child: MaterialApp(
          home: Scaffold(
            body: AgentCard(
              agent: testAgent,
              onSync: () {},
              onForcePulse: () {},
            ),
          ),
        ),
      ),
    );
    expect(find.text('RYUZU'), findsOneWidget);
  });

  testWidgets('AgentCard renders mood', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        child: MaterialApp(
          home: Scaffold(
            body: AgentCard(
              agent: testAgent,
              onSync: () {},
              onForcePulse: () {},
            ),
          ),
        ),
      ),
    );
    expect(find.text('Vigilant'), findsOneWidget);
  });

  testWidgets('AgentCard renders last pulse thought', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        child: MaterialApp(
          home: Scaffold(
            body: AgentCard(
              agent: testAgent,
              onSync: () {},
              onForcePulse: () {},
            ),
          ),
        ),
      ),
    );
    expect(find.text('Scanning for directives...'), findsOneWidget);
  });

  testWidgets('AgentCard shows placeholder when no pulse', (tester) async {
    final agentNoPulse = Map<String, dynamic>.from(testAgent)
      ..['last_pulse'] = null;
    await tester.pumpWidget(
      ProviderScope(
        child: MaterialApp(
          home: Scaffold(
            body: AgentCard(
              agent: agentNoPulse,
              onSync: () {},
              onForcePulse: () {},
            ),
          ),
        ),
      ),
    );
    expect(find.text('Waiting for first pulse...'), findsOneWidget);
  });
}
```

**Step 2: Run test to verify it fails**

```bash
cd voidcat_tether
/c/Users/Wykeve/flutter/bin/flutter test test/agent_card_test.dart
```
Expected: FAIL — `agent_card.dart` doesn't exist yet.

**Step 3: Create `voidcat_tether/lib/features/dashboard/widgets/agent_card.dart`**

```dart
import 'package:flutter/material.dart';

/// Per-agent status panel for the Throne NOC layout.
/// Receives a single agent data map from the STATE_UPDATE payload.
class AgentCard extends StatelessWidget {
  final Map<String, dynamic> agent;
  final VoidCallback onSync;
  final VoidCallback onForcePulse;

  const AgentCard({
    super.key,
    required this.agent,
    required this.onSync,
    required this.onForcePulse,
  });

  Color _moodColor(String mood) {
    switch (mood.toLowerCase()) {
      case 'vigilant':
        return Colors.amber;
      case 'focused':
        return Colors.blueAccent;
      case 'synchronized':
        return Colors.tealAccent;
      case 'neutral':
      default:
        return const Color(0xFF94A3B8);
    }
  }

  @override
  Widget build(BuildContext context) {
    final name = (agent['name'] as String? ?? 'Unknown').toUpperCase();
    final designation = agent['designation'] as String? ?? '';
    final mood = agent['mood'] as String? ?? 'Neutral';
    final uptime = (agent['uptime'] as num? ?? 0).toStringAsFixed(0);
    final lastPulse = agent['last_pulse'] as Map<String, dynamic>?;

    final moodColor = _moodColor(mood);

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B).withOpacity(0.5),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFF334155)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Zone 1: Status
          Row(
            children: [
              Container(
                width: 8,
                height: 8,
                decoration: const BoxDecoration(
                  color: Colors.green,
                  shape: BoxShape.circle,
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  name,
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.bold,
                    fontSize: 14,
                    letterSpacing: 1.2,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            designation,
            style: const TextStyle(
              color: Color(0xFF64748B),
              fontSize: 11,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
            decoration: BoxDecoration(
              color: moodColor.withOpacity(0.1),
              borderRadius: BorderRadius.circular(4),
              border: Border.all(color: moodColor.withOpacity(0.3)),
            ),
            child: Text(
              mood,
              style: TextStyle(
                color: moodColor,
                fontSize: 11,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          const SizedBox(height: 4),
          Text(
            'Uptime: ${uptime}s',
            style: const TextStyle(
              color: Color(0xFF64748B),
              fontSize: 11,
            ),
          ),
          const Divider(color: Color(0xFF334155), height: 20),
          // Zone 2: Last Pulse
          if (lastPulse == null)
            const Text(
              'Waiting for first pulse...',
              style: TextStyle(
                color: Color(0xFF64748B),
                fontSize: 12,
                fontStyle: FontStyle.italic,
              ),
            )
          else ...[
            Row(
              children: [
                Text(
                  _formatTime(lastPulse['timestamp'] as String? ?? ''),
                  style: const TextStyle(
                    color: Color(0xFF64748B),
                    fontSize: 11,
                    fontFamily: 'RobotoMono',
                  ),
                ),
                const SizedBox(width: 8),
                Text(
                  lastPulse['action'] as String? ?? '',
                  style: const TextStyle(
                    color: Colors.orangeAccent,
                    fontSize: 11,
                    fontFamily: 'RobotoMono',
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              lastPulse['thought'] as String? ?? '',
              style: const TextStyle(
                color: Color(0xFFCBD5E1),
                fontSize: 12,
              ),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          ],
          const Divider(color: Color(0xFF334155), height: 20),
          // Zone 3: Actions
          Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: onSync,
                  style: OutlinedButton.styleFrom(
                    foregroundColor: Colors.tealAccent,
                    side: const BorderSide(color: Colors.tealAccent, width: 0.5),
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(6),
                    ),
                  ),
                  child: const Text('SYNC', style: TextStyle(fontSize: 11)),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: OutlinedButton(
                  onPressed: onForcePulse,
                  style: OutlinedButton.styleFrom(
                    foregroundColor: Colors.redAccent,
                    side: const BorderSide(color: Colors.redAccent, width: 0.5),
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(6),
                    ),
                  ),
                  child: const Text('⚡ PULSE', style: TextStyle(fontSize: 11)),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  String _formatTime(String iso) {
    try {
      final dt = DateTime.parse(iso);
      return '${dt.hour.toString().padLeft(2, '0')}:'
          '${dt.minute.toString().padLeft(2, '0')}:'
          '${dt.second.toString().padLeft(2, '0')}';
    } catch (_) {
      return iso;
    }
  }
}
```

**Step 4: Run test to verify it passes**

```bash
/c/Users/Wykeve/flutter/bin/flutter test test/agent_card_test.dart
```
Expected: 4 tests pass.

**Step 5: Commit**

```bash
git add voidcat_tether/lib/features/dashboard/widgets/agent_card.dart \
        voidcat_tether/test/agent_card_test.dart
git commit -m "feat: add AgentCard widget with status/pulse/action zones"
```

---

## Task 5: Flutter — Refactor _ThroneView to 3-Column Grid

**Files:**
- Modify: `voidcat_tether/lib/features/dashboard/dashboard_screen.dart`

**Context:** Replace the old `_ThroneView` (which uses three `StateMonitorCard` widgets for a single agent + global quick-action buttons) with a new version that:
1. Reads the `agents` array from the new `STATE_UPDATE` payload
2. Renders one `AgentCard` per agent in a `Row`
3. Replaces the bottom area with a collapsed log feed (flex: 3) + dominant console (flex: 7)

**Step 1: Rewrite `_ThroneView` in `dashboard_screen.dart`**

Replace the entire `_ThroneView` class with:

```dart
class _ThroneView extends ConsumerWidget {
  const _ThroneView();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dashboardState = ref.watch(dashboardStateProvider);

    return dashboardState.when(
      data: (data) {
        final payload = data['payload'] as Map<String, dynamic>? ?? {};
        final agents = (payload['agents'] as List<dynamic>? ?? [])
            .cast<Map<String, dynamic>>();

        return Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            children: [
              // Agent Grid: one card per agent
              SizedBox(
                height: 260,
                child: agents.isEmpty
                    ? const Center(
                        child: Text('Connecting...',
                            style: TextStyle(color: Color(0xFF64748B))))
                    : Row(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: agents.asMap().entries.map((entry) {
                          final agent = entry.value;
                          final agentId = agent['id'] as String? ?? 'sovereign-001';
                          return Expanded(
                            child: Padding(
                              padding: EdgeInsets.only(
                                left: entry.key == 0 ? 0 : 8,
                                right: entry.key == agents.length - 1 ? 0 : 8,
                              ),
                              child: AgentCard(
                                agent: agent,
                                onSync: () => ref
                                    .read(webSocketServiceProvider)
                                    .sendCommand('GOD_SYNC', {
                                  'spirit': agent['name'],
                                  'agent_id': agentId,
                                }),
                                onForcePulse: () => ref
                                    .read(webSocketServiceProvider)
                                    .sendCommand('GOD_STIMULI', {
                                  'agent_id': agentId,
                                  'content': 'SYSTEM_PING_OVERRIDE',
                                }),
                              ),
                            ),
                          );
                        }).toList(),
                      ),
              ),
              const SizedBox(height: 24),
              // Bottom bar: collapsed logs (flex 3) + GOD MODE console (flex 7)
              const Expanded(
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Expanded(flex: 3, child: LogStreamWidget()),
                    SizedBox(width: 16),
                    Expanded(flex: 7, child: ConsoleWidget()),
                  ],
                ),
              ),
            ],
          ),
        );
      },
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (err, _) => Center(
          child: Text('Error: $err',
              style: const TextStyle(color: Colors.red))),
    );
  }
}
```

Also add the import at the top of `dashboard_screen.dart`:
```dart
import 'widgets/agent_card.dart';
```

Remove the now-unused `_QuickActionBtn` class (it's at the bottom of the file — delete the whole class).

**Step 2: Compile check**

```bash
/c/Users/Wykeve/flutter/bin/flutter analyze voidcat_tether/lib/features/dashboard/dashboard_screen.dart
```
Expected: No errors.

**Step 3: Commit**

```bash
git add voidcat_tether/lib/features/dashboard/dashboard_screen.dart
git commit -m "feat: refactor ThroneView to 3-column agent grid with NOC layout"
```

---

## Task 6: Flutter — Update LogStreamWidget for Multi-Agent Events

**Files:**
- Modify: `voidcat_tether/lib/features/dashboard/widgets/log_stream_widget.dart`

**Context:** The current widget listens for `type == 'HEARTBEAT'` events and shows thought/action from a single agent. In the new system:
- `STATE_UPDATE` events contain all agents and are sent every 2 seconds — do NOT log these (too noisy)
- `HEARTBEAT` events (from the heartbeat service) carry per-agent pulse data and should still be logged
- Each log entry should show: agent name + timestamp + action + thought (collapsed to 3 visible lines)

**Step 1: Update `_LogStreamWidgetState` in `log_stream_widget.dart`**

The key change is adding the agent name to each log entry and limiting visible rows to 3:

In the `ref.listen` callback, update the data extraction:
```dart
ref.listen(dashboardStateProvider, (previous, next) {
  next.whenData((data) {
    if (data['type'] == 'HEARTBEAT') {
      final pulse = data['data'] as Map<String, dynamic>? ?? {};
      setState(() {
        _logs.insert(0, {
          'agent': (pulse['agent_id'] as String? ?? 'sys').toUpperCase().substring(0, 4),
          'timestamp': pulse['timestamp'] ?? '',
          'action': pulse['action'] ?? 'INFO',
          'thought': pulse['thought'] ?? '',
        });
        if (_logs.length > 50) _logs.removeLast();
      });
    }
  });
});
```

In the `ListView.builder`, add the agent name column before timestamp:
```dart
Row(
  crossAxisAlignment: CrossAxisAlignment.start,
  children: [
    SizedBox(
      width: 36,
      child: Text(
        log['agent'] ?? 'SYS',
        style: const TextStyle(
          color: Colors.tealAccent,
          fontFamily: 'RobotoMono',
          fontSize: 10,
          fontWeight: FontWeight.bold,
        ),
      ),
    ),
    // ... rest of existing row (timestamp, action, thought)
  ],
),
```

Limit `itemCount` to show only 3 items max (collapsed):
```dart
itemCount: _logs.length > 3 ? 3 : _logs.length,
```

Add a "[+N more]" footer when there are more than 3 logs:
```dart
if (_logs.length > 3)
  Padding(
    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
    child: Text(
      '[+${_logs.length - 3} more]',
      style: const TextStyle(
        color: Color(0xFF475569),
        fontSize: 10,
        fontFamily: 'RobotoMono',
      ),
    ),
  ),
```

**Step 2: Compile check**

```bash
/c/Users/Wykeve/flutter/bin/flutter analyze voidcat_tether/lib/features/dashboard/widgets/log_stream_widget.dart
```
Expected: No errors.

**Step 3: Commit**

```bash
git add voidcat_tether/lib/features/dashboard/widgets/log_stream_widget.dart
git commit -m "feat: update LogStreamWidget for multi-agent events, show 3 rows collapsed"
```

---

## Task 7: Flutter — Update ConsoleWidget Echo Format

**Files:**
- Modify: `voidcat_tether/lib/features/dashboard/widgets/console_widget.dart`

**Context:** When a command targets a specific agent, the console should echo `GOD_SYNC → Ryuzu: sent` instead of just `Override: Syncing to Ryuzu...`. Small cosmetic change.

**Step 1: Update command echo strings in `_handleCommand`**

Replace:
```dart
setState(() => _consoleOutput.add("Override: Syncing to ${parts[1]}..."));
```
With:
```dart
setState(() => _consoleOutput.add("GOD_SYNC → ${parts[1]}: sent"));
```

Replace:
```dart
setState(() => _consoleOutput.add("Override: Shifting mood to ${parts[1]}..."));
```
With:
```dart
setState(() => _consoleOutput.add("GOD_MOOD → ${parts[1]}: sent"));
```

Replace:
```dart
setState(() => _consoleOutput.add("Injected: $value"));
```
With:
```dart
setState(() => _consoleOutput.add("GOD_STIMULI → sovereign-001: sent"));
```

**Step 2: Compile check**

```bash
/c/Users/Wykeve/flutter/bin/flutter analyze voidcat_tether/lib/features/dashboard/widgets/console_widget.dart
```

**Step 3: Commit**

```bash
git add voidcat_tether/lib/features/dashboard/widgets/console_widget.dart
git commit -m "feat: update ConsoleWidget echo format to show target agent"
```

---

## Task 8: Flutter — PrismPanel Widget

**Files:**
- Create: `voidcat_tether/lib/features/memory/widgets/prism_panel.dart`

**Context:** Left half of the Memory tab. Calls `GET /api/memory/` with optional agent_id, type, search filters. Displays results as a list of memory cards.

**Step 1: Create `voidcat_tether/lib/features/memory/widgets/prism_panel.dart`**

```dart
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../services/handshake_service.dart';

class PrismPanel extends ConsumerStatefulWidget {
  const PrismPanel({super.key});

  @override
  ConsumerState<PrismPanel> createState() => _PrismPanelState();
}

class _PrismPanelState extends ConsumerState<PrismPanel> {
  String? _selectedAgent;
  String? _selectedType;
  String _searchText = '';
  List<Map<String, dynamic>> _memories = [];
  bool _loading = false;
  String? _error;

  final _searchController = TextEditingController();

  static const _agents = ['All', 'Ryuzu', 'Albedo', 'Beatrice'];
  static const _types = ['All', 'fast_stream', 'deep_well'];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; });
    try {
      final handshake = ref.read(handshakeServiceProvider);
      final params = <String, String>{};
      if (_selectedAgent != null && _selectedAgent != 'All') {
        params['agent_id'] = _selectedAgent!;
      }
      if (_selectedType != null && _selectedType != 'All') {
        params['type'] = _selectedType!;
      }
      if (_searchText.isNotEmpty) params['search'] = _searchText;

      final query = params.entries.map((e) => '${e.key}=${Uri.encodeComponent(e.value)}').join('&');
      final resp = await handshake.get('/api/memory/${query.isNotEmpty ? '?$query' : ''}');

      if (resp.statusCode == 200) {
        final data = jsonDecode(resp.body) as Map<String, dynamic>;
        setState(() {
          _memories = (data['memories'] as List<dynamic>)
              .cast<Map<String, dynamic>>();
        });
      } else {
        setState(() { _error = 'HTTP ${resp.statusCode}'; });
      }
    } catch (e) {
      setState(() { _error = e.toString(); });
    } finally {
      setState(() { _loading = false; });
    }
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B).withOpacity(0.5),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFF334155)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _Header(onRefresh: _load),
          _Filters(
            agents: _agents,
            types: _types,
            selectedAgent: _selectedAgent ?? 'All',
            selectedType: _selectedType ?? 'All',
            searchController: _searchController,
            onAgentChanged: (v) { setState(() { _selectedAgent = v; }); _load(); },
            onTypeChanged: (v) { setState(() { _selectedType = v; }); _load(); },
            onSearchSubmit: (v) { setState(() { _searchText = v; }); _load(); },
          ),
          const Divider(color: Color(0xFF334155), height: 1),
          Expanded(child: _Body(loading: _loading, error: _error, memories: _memories)),
        ],
      ),
    );
  }
}

class _Header extends StatelessWidget {
  final VoidCallback onRefresh;
  const _Header({required this.onRefresh});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Row(
        children: [
          const Icon(Icons.hub, color: Colors.pinkAccent, size: 16),
          const SizedBox(width: 8),
          const Text('THE PRISM',
              style: TextStyle(color: Color(0xFF94A3B8), fontSize: 12, fontWeight: FontWeight.bold)),
          const Spacer(),
          IconButton(
            icon: const Icon(Icons.refresh, size: 16, color: Color(0xFF64748B)),
            onPressed: onRefresh,
            padding: EdgeInsets.zero,
            constraints: const BoxConstraints(),
          ),
        ],
      ),
    );
  }
}

class _Filters extends StatelessWidget {
  final List<String> agents;
  final List<String> types;
  final String selectedAgent;
  final String selectedType;
  final TextEditingController searchController;
  final ValueChanged<String?> onAgentChanged;
  final ValueChanged<String?> onTypeChanged;
  final ValueChanged<String> onSearchSubmit;

  const _Filters({
    required this.agents, required this.types,
    required this.selectedAgent, required this.selectedType,
    required this.searchController,
    required this.onAgentChanged, required this.onTypeChanged,
    required this.onSearchSubmit,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
      child: Row(
        children: [
          _Dropdown(value: selectedAgent, items: agents, onChanged: onAgentChanged),
          const SizedBox(width: 8),
          _Dropdown(value: selectedType, items: types, onChanged: onTypeChanged),
          const SizedBox(width: 8),
          Expanded(
            child: SizedBox(
              height: 32,
              child: TextField(
                controller: searchController,
                onSubmitted: onSearchSubmit,
                style: const TextStyle(color: Colors.white, fontSize: 12),
                decoration: InputDecoration(
                  hintText: 'Search...',
                  hintStyle: const TextStyle(color: Color(0xFF64748B), fontSize: 12),
                  filled: true,
                  fillColor: const Color(0xFF0F172A),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(6),
                    borderSide: BorderSide.none,
                  ),
                  contentPadding: const EdgeInsets.symmetric(horizontal: 10),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _Dropdown extends StatelessWidget {
  final String value;
  final List<String> items;
  final ValueChanged<String?> onChanged;

  const _Dropdown({required this.value, required this.items, required this.onChanged});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8),
      height: 32,
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A),
        borderRadius: BorderRadius.circular(6),
      ),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<String>(
          value: value,
          dropdownColor: const Color(0xFF1E293B),
          style: const TextStyle(color: Colors.white, fontSize: 12),
          items: items.map((e) => DropdownMenuItem(value: e, child: Text(e))).toList(),
          onChanged: onChanged,
        ),
      ),
    );
  }
}

class _Body extends StatelessWidget {
  final bool loading;
  final String? error;
  final List<Map<String, dynamic>> memories;

  const _Body({required this.loading, required this.error, required this.memories});

  @override
  Widget build(BuildContext context) {
    if (loading) return const Center(child: CircularProgressIndicator(strokeWidth: 2));
    if (error != null) return Center(child: Text('Error: $error', style: const TextStyle(color: Colors.red, fontSize: 12)));
    if (memories.isEmpty) {
      return const Center(
        child: Text('No memories found', style: TextStyle(color: Color(0xFF64748B), fontSize: 12)),
      );
    }
    return ListView.separated(
      padding: const EdgeInsets.all(12),
      itemCount: memories.length,
      separatorBuilder: (_, __) => const Divider(color: Color(0xFF334155), height: 8),
      itemBuilder: (context, i) {
        final m = memories[i];
        return Padding(
          padding: const EdgeInsets.symmetric(vertical: 4),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Text(
                    (m['agent_id'] as String? ?? '').toUpperCase(),
                    style: const TextStyle(color: Colors.tealAccent, fontSize: 10, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    m['type'] as String? ?? '',
                    style: const TextStyle(color: Color(0xFF64748B), fontSize: 10),
                  ),
                  const Spacer(),
                  Text(
                    _shortTime(m['timestamp'] as String? ?? ''),
                    style: const TextStyle(color: Color(0xFF475569), fontSize: 10),
                  ),
                ],
              ),
              const SizedBox(height: 4),
              Text(
                m['content'] as String? ?? '',
                style: const TextStyle(color: Color(0xFFCBD5E1), fontSize: 12),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ),
        );
      },
    );
  }

  String _shortTime(String iso) {
    try {
      return DateTime.parse(iso).toLocal().toString().substring(11, 19);
    } catch (_) {
      return iso;
    }
  }
}
```

**Step 2: Compile check**

```bash
/c/Users/Wykeve/flutter/bin/flutter analyze voidcat_tether/lib/features/memory/widgets/prism_panel.dart
```
Expected: No errors. (You may need to create the `lib/features/memory/widgets/` directory first.)

**Step 3: Commit**

```bash
git add voidcat_tether/lib/features/memory/widgets/prism_panel.dart
git commit -m "feat: add PrismPanel widget for memory browser"
```

---

## Task 9: Flutter — StasisPanel Widget

**Files:**
- Create: `voidcat_tether/lib/features/memory/widgets/stasis_panel.dart`

**Step 1: Create the file**

```dart
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../services/handshake_service.dart';

class StasisPanel extends ConsumerStatefulWidget {
  const StasisPanel({super.key});

  @override
  ConsumerState<StasisPanel> createState() => _StasisPanelState();
}

class _StasisPanelState extends ConsumerState<StasisPanel> {
  List<Map<String, dynamic>> _snapshots = [];
  bool _loading = false;
  String? _error;
  String? _restoringId;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; });
    try {
      final handshake = ref.read(handshakeServiceProvider);
      final resp = await handshake.get('/api/stasis/');
      if (resp.statusCode == 200) {
        final data = jsonDecode(resp.body) as Map<String, dynamic>;
        setState(() {
          _snapshots = (data['snapshots'] as List<dynamic>)
              .cast<Map<String, dynamic>>();
        });
      } else {
        setState(() { _error = 'HTTP ${resp.statusCode}'; });
      }
    } catch (e) {
      setState(() { _error = e.toString(); });
    } finally {
      setState(() { _loading = false; });
    }
  }

  Future<void> _restore(String agentId) async {
    setState(() { _restoringId = agentId; });
    try {
      final handshake = ref.read(handshakeServiceProvider);
      final resp = await handshake.post('/api/stasis/$agentId/restore', {});
      if (resp.statusCode == 200) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('$agentId restored'), backgroundColor: Colors.teal),
        );
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Restore failed: ${resp.statusCode}'), backgroundColor: Colors.red),
        );
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: $e'), backgroundColor: Colors.red),
      );
    } finally {
      setState(() { _restoringId = null; });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B).withOpacity(0.5),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFF334155)),
      ),
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            child: Row(
              children: [
                const Icon(Icons.ac_unit, color: Colors.blueAccent, size: 16),
                const SizedBox(width: 8),
                const Text('STASIS CHAMBER',
                    style: TextStyle(
                        color: Color(0xFF94A3B8),
                        fontSize: 12,
                        fontWeight: FontWeight.bold)),
                const Spacer(),
                IconButton(
                  icon: const Icon(Icons.refresh, size: 16, color: Color(0xFF64748B)),
                  onPressed: _load,
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(),
                ),
              ],
            ),
          ),
          const Divider(color: Color(0xFF334155), height: 1),
          Expanded(child: _buildBody()),
        ],
      ),
    );
  }

  Widget _buildBody() {
    if (_loading) {
      return const Center(child: CircularProgressIndicator(strokeWidth: 2));
    }
    if (_error != null) {
      return Center(
        child: Text('Error: $_error',
            style: const TextStyle(color: Colors.red, fontSize: 12)));
    }
    if (_snapshots.isEmpty) {
      return const Center(
        child: Text('No stasis snapshots found',
            style: TextStyle(color: Color(0xFF64748B), fontSize: 12)));
    }
    return ListView.separated(
      padding: const EdgeInsets.all(12),
      itemCount: _snapshots.length,
      separatorBuilder: (_, __) => const Divider(color: Color(0xFF334155), height: 8),
      itemBuilder: (context, i) {
        final s = _snapshots[i];
        final agentId = s['agent_id'] as String;
        final modified = _shortDate(s['modified'] as String? ?? '');
        final isRestoring = _restoringId == agentId;

        return Row(
          children: [
            const Icon(Icons.save, size: 14, color: Color(0xFF64748B)),
            const SizedBox(width: 8),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    agentId,
                    style: const TextStyle(
                        color: Colors.white,
                        fontSize: 13,
                        fontWeight: FontWeight.w600),
                  ),
                  Text(
                    modified,
                    style: const TextStyle(
                        color: Color(0xFF64748B), fontSize: 11),
                  ),
                ],
              ),
            ),
            isRestoring
                ? const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2))
                : TextButton(
                    onPressed: () => _restore(agentId),
                    style: TextButton.styleFrom(
                      foregroundColor: Colors.blueAccent,
                      padding: const EdgeInsets.symmetric(horizontal: 8),
                    ),
                    child: const Text('RESTORE', style: TextStyle(fontSize: 11)),
                  ),
          ],
        );
      },
    );
  }

  String _shortDate(String iso) {
    try {
      return DateTime.parse(iso).toLocal().toString().substring(0, 16);
    } catch (_) {
      return iso;
    }
  }
}
```

**Step 2: Compile check and commit**

```bash
/c/Users/Wykeve/flutter/bin/flutter analyze voidcat_tether/lib/features/memory/widgets/stasis_panel.dart
git add voidcat_tether/lib/features/memory/widgets/stasis_panel.dart
git commit -m "feat: add StasisPanel widget for stasis snapshot management"
```

---

## Task 10: Flutter — MemoryScreen + Wire Into Nav

**Files:**
- Create: `voidcat_tether/lib/features/memory/memory_screen.dart`
- Modify: `voidcat_tether/lib/features/dashboard/dashboard_screen.dart`
- Delete: `voidcat_tether/lib/features/dashboard/widgets/memory_view.dart` (replaced)

**Step 1: Create `memory_screen.dart`**

```dart
import 'package:flutter/material.dart';
import 'widgets/prism_panel.dart';
import 'widgets/stasis_panel.dart';

class MemoryScreen extends StatelessWidget {
  const MemoryScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(24.0),
      child: const Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Expanded(flex: 1, child: PrismPanel()),
          SizedBox(width: 16),
          Expanded(flex: 1, child: StasisPanel()),
        ],
      ),
    );
  }
}
```

**Step 2: Update `dashboard_screen.dart` — replace MemoryView with MemoryScreen**

In `dashboard_screen.dart`:
1. Remove: `import 'widgets/memory_view.dart';`
2. Add: `import '../../memory/memory_screen.dart';`
3. In `_DesktopDashboardState.build()`, find `const MemoryView()` and replace with `const MemoryScreen()`

**Step 3: Delete the old placeholder**

```bash
rm voidcat_tether/lib/features/dashboard/widgets/memory_view.dart
```

**Step 4: Compile check**

```bash
/c/Users/Wykeve/flutter/bin/flutter analyze voidcat_tether/lib/
```
Expected: No errors.

**Step 5: Commit**

```bash
git add voidcat_tether/lib/features/memory/ \
        voidcat_tether/lib/features/dashboard/dashboard_screen.dart
git rm voidcat_tether/lib/features/dashboard/widgets/memory_view.dart
git commit -m "feat: add MemoryScreen with Prism + Stasis panels, wire into nav"
```

---

## Task 11: Build + Deploy

**Step 1: Fix the stale widget test**

The default `test/widget_test.dart` references a counter widget that doesn't exist. Replace it:

```dart
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('placeholder — no widget tests to run at root level', () {
    expect(true, isTrue);
  });
}
```

**Step 2: Run all tests**

```bash
cd voidcat_tether
/c/Users/Wykeve/flutter/bin/flutter test
```
Expected: All pass (agent_card_test.dart + placeholder widget_test.dart).

**Step 3: Build Flutter web**

```bash
/c/Users/Wykeve/flutter/bin/flutter build web --release
```
Expected: `✓ Built build/web` with no errors.

**Step 4: Copy build output to src/static/**

```bash
cp -r build/web/. ../src/static/
```

**Step 5: Rebuild Docker container**

```bash
cd ..
docker compose up middleware --build -d
sleep 5
curl -s http://localhost:8090/health
```
Expected: `{"database":"connected","graph":"connected"}`

**Step 6: Verify in browser**

Open `http://localhost:8090` in Chrome. Confirm:
- Three agent cards visible at 1400px width
- Each card shows agent name, mood, uptime
- SYSTEM LOGS shows 3 rows collapsed with "[+N more]"
- GOD MODE console takes 70% of bottom bar
- Memory tab shows Prism + Stasis panels side by side

**Step 7: Commit final build**

```bash
git add src/static/ voidcat_tether/test/widget_test.dart
git commit -m "feat: deploy Throne NOC dashboard v2 — 3-agent grid, Memory tab"
```

---

## Sequence Summary

```
Task 1  → Backend multi-agent STATE_UPDATE
Task 2  → Backend /api/memory/ endpoint
Task 3  → Backend /api/stasis/ endpoints
Task 4  → Flutter AgentCard widget + tests
Task 5  → Flutter refactor _ThroneView
Task 6  → Flutter LogStreamWidget update
Task 7  → Flutter ConsoleWidget echo format
Task 8  → Flutter PrismPanel
Task 9  → Flutter StasisPanel
Task 10 → Flutter MemoryScreen + nav wiring
Task 11 → Build + deploy + verify
```

Tasks 1-3 can be done before any Flutter work. Tasks 4-10 are all independent Flutter widgets that can be written in any order. Task 11 is last.
