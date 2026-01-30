# Technical Specification: Phase 5 Higher Functions Implementation

## Technical Context
- **Language**: Python 3.x (backend), JavaScript/React (frontend)
- **Framework**: FastAPI (backend), React (frontend)
- **Databases**: PostgreSQL (state), Neo4j (knowledge graph), Weaviate (vector memory), Redis (cache/pubsub)
- **Dependencies**: See requirements.txt for full list including httpx, pydantic, weaviate-client, etc.
- **Architecture**: Microservices with Docker containerization, WebSocket for real-time communication

## Implementation Approach
Implement the 4 open features from Phase 5 in tobefixed.md:
1. Replace placeholder memory endpoint with actual Weaviate integration
2. Implement functional Chat and Config components in React frontend
3. Add WebSocket auto-reconnection logic to frontend
4. Add transaction/rollback logic to Spirit Sync endpoint

Approach: Incremental implementation with testing at each step. Backend changes first, then frontend.

## Source Code Structure Changes
- `src/api/agents.py`: Update memory endpoint (lines 217-228) to query Weaviate instead of returning demo data
- `src/web_ui/src/App.jsx`: Replace placeholder components with functional Chat and Config routes
- `src/web_ui/src/pages/Dashboard.jsx`: Add WebSocket reconnection logic
- `src/core/identity/manager.py`: Implement rollback mechanism for Spirit Sync failures

## Data Model / API / Interface Changes
- Memory endpoint: Change from static demo response to dynamic Weaviate GraphQL queries
- Frontend: Add state management for chat messages and config settings
- WebSocket: Add reconnection state and retry logic
- Spirit Sync: Add database transaction wrapper with rollback on partial failures

## Verification Approach
- Unit tests for backend endpoints using pytest
- Integration tests for Weaviate queries
- Frontend tests for React components
- Manual testing of WebSocket reconnection
- Run existing test suite: `pytest`
- Lint check: `pylint src/`
- Type check: `mypy src/`