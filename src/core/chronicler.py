"""
VoidCat RDC: Sovereign Spirit Core - The Chronicler
===================================================
Version: 1.0.0
Author: Echo (E-01)
Date: 2026-01-24

The Historian of the Pantheon. Aggregates disparate event streams 
(heartbeats, messages, signals) into a unified timeline for visualization.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel
from sqlalchemy import text

from src.core.database import get_database

logger = logging.getLogger("sovereign.chronicler")

# =============================================================================
# Models
# =============================================================================

class TimelineEvent(BaseModel):
    """Normalized event for the timeline."""
    event_id: str
    timestamp: datetime
    actor_name: str
    actor_id: str
    event_type: str  # 'HEARTBEAT', 'MESSAGE_SENT', 'MESSAGE_RECEIVED'
    summary: str
    details: Optional[str] = None
    metadata: Dict[str, Any] = {}

class PantheonSnapshot(BaseModel):
    """Snapshot of the current state of all agents."""
    timestamp: datetime
    agents: List[Dict[str, Any]]
    active_count: int

# =============================================================================
# The Chronicler
# =============================================================================

class Chronicler:
    """aggregates history for visualization."""

    def __init__(self):
        self.db = get_database()

    async def get_timeline(self, limit: int = 100) -> List[TimelineEvent]:
        """
        Fetch and merge events from all sources into a Chronological timeline.
        Uses a UNION query for efficiency (single round-trip).
        Ordered by timestamp DESC (newest first).
        """
        if not self.db._initialized:
            await self.db.initialize()

        events: List[TimelineEvent] = []

        async with self.db.session() as session:
            # Unified UNION query - single round-trip instead of N+1
            unified_query = text("""
                (
                    SELECT
                        h.id::text as event_id,
                        h.created_at as timestamp,
                        a.name as actor_name,
                        a.id::text as actor_id,
                        'HEARTBEAT' as event_type,
                        h.action_taken as action_or_status,
                        h.thought_content as content,
                        NULL::text as target_id
                    FROM heartbeat_logs h
                    JOIN agents a ON h.agent_id = a.id
                )
                UNION ALL
                (
                    SELECT
                        m.id::text as event_id,
                        m.created_at as timestamp,
                        a.name as actor_name,
                        a.id::text as actor_id,
                        'MESSAGE_SENT' as event_type,
                        m.status as action_or_status,
                        m.content as content,
                        m.to_agent_id::text as target_id
                    FROM agent_messages m
                    JOIN agents a ON m.from_agent_id = a.id
                )
                ORDER BY timestamp DESC
                LIMIT :limit
            """)

            result = await session.execute(unified_query, {"limit": limit})

            for row in result:
                if row.event_type == "HEARTBEAT":
                    events.append(TimelineEvent(
                        event_id=row.event_id,
                        timestamp=row.timestamp,
                        actor_name=row.actor_name,
                        actor_id=row.actor_id,
                        event_type="HEARTBEAT",
                        summary=f"Pulse: {row.action_or_status}",
                        details=row.content,
                        metadata={"action": row.action_or_status}
                    ))
                else:
                    events.append(TimelineEvent(
                        event_id=row.event_id,
                        timestamp=row.timestamp,
                        actor_name=row.actor_name,
                        actor_id=row.actor_id,
                        event_type="MESSAGE_SENT",
                        summary=f"Sent Message ({row.action_or_status})",
                        details=row.content,
                        metadata={
                            "status": row.action_or_status,
                            "to_agent_id": row.target_id
                        }
                    ))

        return events

#Singleton
_chronicler: Optional[Chronicler] = None

def get_chronicler() -> Chronicler:
    global _chronicler
    if _chronicler is None:
        _chronicler = Chronicler()
    return _chronicler
