"""
VoidCat RDC: Sovereign Spirit - Memory API Router
==================================================
Exposes the Prism's episodic memory log over HTTP for The Throne NOC dashboard.

Endpoint
--------
GET /api/memory/
    Query stored memories from the memory_events table via the PrismEngine.
    Supports optional filtering by agent_id, type, and search term.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from src.core.memory.prism import get_prism

logger = logging.getLogger("sovereign.api.memory")

router = APIRouter(prefix="/api/memory", tags=["memory"])

# =============================================================================
# Response Models
# =============================================================================


class MemoryItem(BaseModel):
    """A single episodic memory record returned by the API."""

    id: str
    agent_id: str
    content: str
    type: str
    timestamp: Optional[str] = None
    emotional_valence: float = 0.0


class MemoryListResponse(BaseModel):
    """Paginated list of memories."""

    memories: List[MemoryItem]
    count: int
    error: Optional[str] = None


# =============================================================================
# Endpoint
# =============================================================================


@router.get(
    "/",
    response_model=MemoryListResponse,
    summary="List stored memories from the Prism",
    description=(
        "Query episodic memories from the memory_events table. "
        "Filter by agent_id, memory type, or a search term."
    ),
)
async def list_memories(
    agent_id: Optional[str] = Query(
        default=None,
        description="Filter by agent name (case-insensitive).",
    ),
    type: Optional[str] = Query(  # noqa: A002  — intentional; maps to event_type
        default=None,
        alias="type",
        description="Filter by memory type / event_type (e.g. 'observation', 'action').",
    ),
    search: Optional[str] = Query(
        default=None,
        description="Full-text substring search on memory content.",
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of memories to return (1-100).",
    ),
) -> MemoryListResponse:
    """
    Return a list of stored episodic memories from the Prism's PostgreSQL store.

    Empty list is a valid result when no memories have been recorded yet.
    Never raises a 500 — errors are returned in the `error` field.
    """
    prism = get_prism()

    try:
        raw: List[Dict[str, Any]] = await prism.list_memories(
            agent_id=agent_id,
            memory_type=type,
            search=search,
            limit=limit,
        )
    except Exception as exc:
        logger.error(f"Memory endpoint error: {exc}")
        return MemoryListResponse(memories=[], count=0, error=str(exc))

    items = [
        MemoryItem(
            id=row.get("id", ""),
            agent_id=row.get("agent_id", "unknown"),
            content=row.get("content", ""),
            type=row.get("type", "observation"),
            timestamp=row.get("timestamp"),
            emotional_valence=float(row.get("emotional_valence") or 0.0),
        )
        for row in raw
    ]

    logger.info(
        f"Memory query: agent_id={agent_id!r} type={type!r} "
        f"search={search!r} limit={limit} -> {len(items)} results"
    )

    return MemoryListResponse(memories=items, count=len(items))
