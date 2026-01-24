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
        Ordered by timestamp DESC (newest first).
        """
        if not self.db._initialized:
            await self.db.initialize()

        events: List[TimelineEvent] = []

        async with self.db.session() as session:
            # 1. Fetch Heartbeats
            hb_query = text("""
                SELECT h.id, h.created_at, a.name, a.id as agent_uuid, 
                       h.action_taken, h.thought_content
                FROM heartbeat_logs h
                JOIN agents a ON h.agent_id = a.id
                ORDER BY h.created_at DESC
                LIMIT :limit
            """)
            hb_result = await session.execute(hb_query, {"limit": limit})
            
            for row in hb_result:
                events.append(TimelineEvent(
                    event_id=str(row.id),
                    timestamp=row.created_at,
                    actor_name=row.name,
                    actor_id=str(row.agent_uuid),
                    event_type="HEARTBEAT",
                    summary=f"Pulse: {row.action_taken}",
                    details=row.thought_content,
                    metadata={"action": row.action_taken}
                ))

            # 2. Fetch Messages (Sent)
            msg_query = text("""
                SELECT m.id, m.created_at, a.name, a.id as agent_uuid,
                       m.content, m.status, m.to_agent_id
                FROM agent_messages m
                JOIN agents a ON m.from_agent_id = a.id
                ORDER BY m.created_at DESC
                LIMIT :limit
            """)
            msg_result = await session.execute(msg_query, {"limit": limit})
            
            for row in msg_result:
                # Try to resolve target name if possible (simple optimization)
                target_name = "Unknown"
                # We could join again, but for now let's keep it simple or do a separate lookup dict if needed.
                # actually, 'to_agent_id' is a UUID. 
                
                events.append(TimelineEvent(
                    event_id=str(row.id),
                    timestamp=row.created_at,
                    actor_name=row.name,
                    actor_id=str(row.agent_uuid),
                    event_type="MESSAGE_SENT",
                    summary=f"Sent Message ({row.status})",
                    details=row.content,
                    metadata={"status": row.status, "to_agent_id": str(row.to_agent_id) if row.to_agent_id else None}
                ))

        # 3. Sort merged list by timestamp DESC
        events.sort(key=lambda x: x.timestamp, reverse=True)
        
        # Return top N after merge
        return events[:limit]

#Singleton
_chronicler: Optional[Chronicler] = None

def get_chronicler() -> Chronicler:
    global _chronicler
    if _chronicler is None:
        _chronicler = Chronicler()
    return _chronicler
