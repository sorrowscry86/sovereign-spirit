"""
Messages API Router (DEPRECATED)

Legacy bidirectional communication endpoints. Superseded by the Tether protocol
(/api/tether/*) which provides thread-based messaging with read-state tracking.

These routes remain functional for backward compatibility but will be removed
in a future release. Migrate to /api/tether/send and /api/tether/threads.
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.core.database import get_database
from src.core.heartbeat.service import get_heartbeat_service
from src.core.identity.manager import get_identity_manager
from sqlalchemy import text

logger = logging.getLogger("sovereign.messages")

router = APIRouter(
    prefix="/api/messages",
    tags=["messages (deprecated)"],
    deprecated=True,
)


# Request/Response Models
class SendMessageRequest(BaseModel):
    content: str
    agent_id: str = "sovereign-001"


class MessageResponse(BaseModel):
    id: str
    sender: str
    content: str
    timestamp: str
    agent_id: str
    thought_id: Optional[str] = None


class MessageListResponse(BaseModel):
    messages: list[MessageResponse]
    count: int


@router.post("/send", response_model=MessageResponse, deprecated=True)
async def send_message(request: SendMessageRequest):
    """
    Send a message to the Sovereign Spirit.

    .. deprecated:: 1.2.0
        Use POST /api/tether/send instead.
    """
    db = get_database()

    msg_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    # Save to database
    async with db.session() as session:
        await session.execute(
            text("""
                INSERT INTO messages (id, sender, content, timestamp, agent_id)
                VALUES (:id, :sender, :content, :timestamp, :agent_id)
            """),
            {
                "id": msg_id,
                "sender": "user",
                "content": request.content,
                "timestamp": now,
                "agent_id": request.agent_id,
            },
        )

    # Fluid Persona: Evaluate Context and Switch Identity if needed
    try:
        identity_manager = get_identity_manager(db)
        current_state = await db.get_agent_state(request.agent_id)
        current_spirit = current_state.designation if current_state else "Echo"
        await identity_manager.evaluate_and_sync(
            agent_id=request.agent_id,
            current_spirit=current_spirit,
            user_message=request.content,
        )
    except Exception as e:
        logger.warning(f"Fluid Persona evaluation failed: {e}")

    # Trigger heartbeat pulse with user message
    heartbeat = get_heartbeat_service()
    try:
        await heartbeat.trigger_once(request.agent_id, user_message=request.content)
    except Exception as e:
        logger.warning(f"Heartbeat trigger failed: {e}")

    return MessageResponse(
        id=msg_id,
        sender="user",
        content=request.content,
        timestamp=now.isoformat(),
        agent_id=request.agent_id,
        thought_id=None,
    )


@router.get("/history", response_model=MessageListResponse, deprecated=True)
async def get_message_history(limit: int = 50, agent_id: Optional[str] = None):
    """
    Retrieve conversation history.

    .. deprecated:: 1.2.0
        Use GET /api/tether/threads/:id/messages instead.
    """
    db = get_database()

    async with db.session() as session:
        if agent_id:
            result = await session.execute(
                text("""
                    SELECT id, sender, content, timestamp, agent_id, thought_id
                    FROM messages
                    WHERE agent_id = :agent_id
                    ORDER BY timestamp DESC
                    LIMIT :limit
                """),
                {"agent_id": agent_id, "limit": limit},
            )
        else:
            result = await session.execute(
                text("""
                    SELECT id, sender, content, timestamp, agent_id, thought_id
                    FROM messages
                    ORDER BY timestamp DESC
                    LIMIT :limit
                """),
                {"limit": limit},
            )

        rows = result.mappings().all()

    messages = [
        MessageResponse(
            id=str(row["id"]),
            sender=row["sender"],
            content=row["content"],
            timestamp=(
                row["timestamp"].isoformat()
                if hasattr(row["timestamp"], "isoformat")
                else str(row["timestamp"])
            ),
            agent_id=row["agent_id"],
            thought_id=row.get("thought_id"),
        )
        for row in rows
    ]

    return MessageListResponse(messages=messages, count=len(messages))


@router.get("/{message_id}", response_model=MessageResponse, deprecated=True)
async def get_message(message_id: str):
    """
    Get a specific message by ID.

    .. deprecated:: 1.2.0
        Use GET /api/tether/threads/:id/messages instead.
    """
    db = get_database()

    async with db.session() as session:
        result = await session.execute(
            text("""
                SELECT id, sender, content, timestamp, agent_id, thought_id
                FROM messages
                WHERE id = :id
            """),
            {"id": message_id},
        )
        row = result.mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="Message not found")

    return MessageResponse(
        id=str(row["id"]),
        sender=row["sender"],
        content=row["content"],
        timestamp=(
            row["timestamp"].isoformat()
            if hasattr(row["timestamp"], "isoformat")
            else str(row["timestamp"])
        ),
        agent_id=row["agent_id"],
        thought_id=row.get("thought_id"),
    )
