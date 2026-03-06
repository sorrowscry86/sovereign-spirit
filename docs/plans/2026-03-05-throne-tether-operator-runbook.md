# Throne x Tether Operator Runbook
**Date:** 2026-03-05
**Scope:** Text-only operational handoff for the Throne revamp track
**State:** Active operations baseline

## Purpose
Provide a clean, deterministic operating baseline for inspection, validation, and safe iteration.

## Current Reality
- Backend Tether protocol is active (`/api/tether/*`, `TETHER_JOIN`, `TETHER_SEND`, `TETHER_READ`).
- Legacy paths still exist for continuity (`/api/messages/*`, `GOD_*` websocket commands).
- Frontend source of truth is present (`voidcat_tether/lib` restored).
- Compiled artifacts are present in `src/static/` and must not be treated as editable source.

## Change Gate Status
Implementation gate was satisfied and closed. Changes are now in post-cutover validation mode.

1. Source restoration strategy: completed.
2. Deprecation policy: active (`/api/messages/*` deprecated, not removed).
3. Test scope: partially complete (runtime checks done, automated integration tests pending).
4. Rollback criteria: still authoritative (see section below).

## Rollback Criteria
Rollback to legacy flow if any condition is true during cutover testing:

1. `TETHER_SEND` accepted but no heartbeat reply appears in the same thread within expected cycle.
2. Message status transition (`pending -> delivered -> read`) is missing or inconsistent.
3. Thread subscription events fail (`TETHER_JOIN` succeeds but no `TETHER_MESSAGE` broadcast observed).
4. UI cannot load historical thread messages from `/api/tether/threads/{thread_id}/messages`.

## Manual Verification Checklist (Current)
1. Confirm Throne loads from `/` and WebSocket connects to `/ws/dashboard`.
2. Confirm thread list and timeline interactions use `/api/tether/*` plus `TETHER_*` websocket commands.
3. Confirm GOD panel commands still process (`GOD_SYNC`, `GOD_MOOD`, `GOD_STIMULI`) during grace window.

## Manual Verification Checklist (Post-Implementation)
1. Create thread, send user message, receive agent response in same thread timeline.
2. Mark read and verify `MSG_STATUS_UPDATE` event payload.
3. Confirm legacy `/api/messages/*` still operational during grace window.
4. Confirm rebuild pipeline regenerates `src/static/` from restored source.

## Handoff Artifacts
- Revamp initialization plan: `docs/plans/2026-03-05-throne-tether-revamp-init.md`
- Tether implementation record: `docs/plans/2026-03-05-tether-protocol.md`
- Project tracker: `tobefixed.md`

## Confirmation Template
Historical approval format used to open implementation:

`APPROVED: WS1 source restoration may begin. Non-code prep complete. Proceed with code changes.`
