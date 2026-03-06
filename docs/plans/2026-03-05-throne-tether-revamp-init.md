# Throne x Tether Revamp - Initialization and Preparation
**Date:** 2026-03-05
**Status:** Implemented and active (post-cutover validation)
**Owner:** The Throne Revamp Track

## Objective
Revamp the Throne dashboard to use the unified Tether protocol for thread-based communication, inbox state, and live websocket thread events.

## Preflight Findings
- Backend is ready for Tether chat flows.
- `/api/tether/*` routes are present and active.
- `/ws/dashboard` supports `TETHER_JOIN`, `TETHER_SEND`, and `TETHER_READ`.
- Legacy GOD_MODE commands remain in place for operational continuity.
- Throne source code is present in repository (`voidcat_tether/lib` restored).
- `src/static/` contains compiled Flutter web artifacts (`main.dart.js`, `flutter_bootstrap.js`, canvaskit files).

## Architectural Decision
Do not edit compiled `src/static/main.dart.js` directly.

Canonical source is restored and tracked under `voidcat_tether/` so future Throne updates are deterministic, reviewable, and testable.

## Workstreams
### WS1 - Source Resurrection
- Rehydrated Flutter project source in `voidcat_tether/`.
- Restored app structure (`lib/`, `pubspec.yaml`).
- Confirmed `flutter build web` reproduces `src/static/` payload.

### WS2 - Protocol Client Layer
- Implemented a Tether client service for:
  - `GET /api/tether/threads`
  - `GET /api/tether/threads/{thread_id}/messages`
  - `POST /api/tether/threads/{thread_id}/messages`
  - `POST /api/tether/send`
  - `GET /api/tether/inbox/{agent_id}`
  - `POST /api/tether/inbox/{agent_id}/read`
- Added websocket command wrappers for:
  - `TETHER_JOIN`
  - `TETHER_SEND`
  - `TETHER_READ`

### WS3 - Throne UI Cutover
- Added thread list pane (agent scoped).
- Added thread timeline pane with sender and status badges.
- Added compose bar with send and optimistic append.
- Added read-state acknowledgements (`MSG_STATUS_UPDATE`).
- Kept GOD controls in a separate command panel (no silent removal).

### WS4 - Compatibility and Deprecation
- Marked `src/api/messages.py` endpoints as deprecated after Throne cutover validation.
- Kept legacy websocket GOD commands for continuity window.
- Final removal conditions remain pending telemetry confirmation.

### WS5 - Verification
- Runtime validation completed for:
  - join thread
  - send tether message
  - receive thread broadcast
  - mark read and receive status update
- Heartbeat response loop from Tether inbox validated in live operation.

## Exit Criteria
- Throne UI fully uses Tether routes and thread websocket events.
- User to agent and agent to user exchanges visible in one thread timeline.
- Read and delivered transitions visible in UI state.
- Legacy `/api/messages/*` routes safely deprecated.
- Build pipeline regenerates `src/static/` from tracked source.

## Immediate Next Action
Formalize automated integration coverage for the join/send/read websocket flow and heartbeat response loop under `tests/`.

## Confirmation Gate (Hard Stop)
Closed. Code changes were authorized and executed.

- Runbook: `docs/plans/2026-03-05-throne-tether-operator-runbook.md`
- Approval text used:
  - `APPROVED: WS1 source restoration may begin. Non-code prep complete. Proceed with code changes.`
