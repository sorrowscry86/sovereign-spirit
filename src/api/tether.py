"""
Tether Protocol API Router
===========================
Unified communication layer for user-agent and agent-agent messaging.
Replaces the fragmented messages + agent_messages system with threaded
conversations, real-time delivery, and full inbox support.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.core.database import get_database
from src.core.cache import get_cache
from src.core.heartbeat.service import get_heartbeat_service
from src.core.identity.manager import get_identity_manager
from src.core.socket_manager import get_connection_manager

logger = logging.getLogger("sovereign.tether")

router = APIRouter(prefix="/api/tether", tags=["tether"])


# =============================================================================
# Request/Response Models
# =============================================================================


class CreateThreadRequest(BaseModel):
    thread_type: str = "user_agent"
    subject: Optional[str] = None
    agent_ids: List[str] = Field(default_factory=list)


class ThreadResponse(BaseModel):
    id: str
    thread_type: str
    subject: Optional[str] = None
    created_by: str
    created_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None
    message_count: int = 0
    participants: List[dict] = Field(default_factory=list)


class PostMessageRequest(BaseModel):
    content: str
    sender_name: str = "User"
    sender_type: str = "user"
    message_type: str = "chat"
    reply_to: Optional[str] = None
    recipient_agent_id: Optional[str] = None


class TetherMessageResponse(BaseModel):
    id: str
    thread_id: str
    sender_name: str
    sender_type: str
    content: str
    message_type: str
    status: str
    reply_to: Optional[str] = None
    created_at: Optional[datetime] = None


class MessageListResponse(BaseModel):
    messages: List[TetherMessageResponse]
    count: int


class SendDirectRequest(BaseModel):
    agent_id: str
    content: str
    sender_name: str = "User"


class InboxResponse(BaseModel):
    messages: List[dict]
    count: int


class MarkReadRequest(BaseModel):
    message_ids: List[str]


# =============================================================================
# Thread Endpoints
# =============================================================================


@router.post("/threads", response_model=ThreadResponse)
async def create_thread(request: CreateThreadRequest) -> ThreadResponse:
    """Create a new conversation thread."""
    db = get_database()

    thread_id = await db.create_tether_thread(
        thread_type=request.thread_type,
        created_by="user",
        subject=request.subject,
    )

    if not thread_id:
        raise HTTPException(status_code=500, detail="Failed to create thread")

    for agent_id in request.agent_ids:
        await db.add_tether_participant(thread_id, agent_id)

    thread = await db.get_tether_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=500, detail="Thread created but not found")

    return ThreadResponse(**thread)


@router.get("/threads", response_model=List[ThreadResponse])
async def list_threads(
    agent_id: Optional[str] = None,
    thread_type: Optional[str] = None,
    limit: int = 20,
) -> List[ThreadResponse]:
    """List conversation threads, optionally filtered."""
    db = get_database()
    threads = await db.list_tether_threads(
        agent_id=agent_id,
        thread_type=thread_type,
        limit=limit,
    )
    return [ThreadResponse(**t) for t in threads]


@router.get("/threads/{thread_id}", response_model=ThreadResponse)
async def get_thread(thread_id: str) -> ThreadResponse:
    """Get a single thread with its participants."""
    db = get_database()
    thread = await db.get_tether_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    return ThreadResponse(**thread)


# =============================================================================
# Message Endpoints
# =============================================================================


@router.post(
    "/threads/{thread_id}/messages",
    response_model=TetherMessageResponse,
)
async def post_message_to_thread(
    thread_id: str,
    request: PostMessageRequest,
) -> TetherMessageResponse:
    """Post a message to an existing thread."""
    db = get_database()
    cache = get_cache()

    thread = await db.get_tether_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    # Resolve sender agent UUID if sender is an agent
    sender_agent_id = None
    if request.sender_type == "agent":
        sender_agent_id = await db.get_agent_uuid(request.sender_name)

    # Resolve recipient agent UUID
    recipient_uuid = None
    if request.recipient_agent_id:
        recipient_uuid = await db.get_agent_uuid(request.recipient_agent_id)

    msg_id = await db.post_tether_message(
        thread_id=thread_id,
        sender_type=request.sender_type,
        sender_name=request.sender_name,
        content=request.content,
        message_type=request.message_type,
        sender_agent_id=sender_agent_id,
        recipient_agent_id=recipient_uuid,
        reply_to=request.reply_to,
    )

    if not msg_id:
        raise HTTPException(status_code=500, detail="Failed to post message")

    # Signal Redis inbox for recipient agents
    if recipient_uuid:
        await cache.signal_tether_inbox(request.recipient_agent_id, msg_id)
    else:
        # Broadcast to all thread participants
        for participant in thread.get("participants", []):
            agent_uuid = await db.get_agent_uuid(participant["name"])
            if agent_uuid and agent_uuid != sender_agent_id:
                await cache.signal_tether_inbox(participant["name"], msg_id)

    # Broadcast via WebSocket
    ws_manager = get_connection_manager()
    await ws_manager.broadcast_to_thread(
        thread_id,
        "TETHER_MESSAGE",
        {
            "id": msg_id,
            "thread_id": thread_id,
            "sender_name": request.sender_name,
            "sender_type": request.sender_type,
            "content": request.content,
            "message_type": request.message_type,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    return TetherMessageResponse(
        id=msg_id,
        thread_id=thread_id,
        sender_name=request.sender_name,
        sender_type=request.sender_type,
        content=request.content,
        message_type=request.message_type,
        status="pending",
        reply_to=request.reply_to,
        created_at=datetime.now(timezone.utc),
    )


@router.get(
    "/threads/{thread_id}/messages",
    response_model=MessageListResponse,
)
async def get_thread_messages(
    thread_id: str,
    before: Optional[str] = None,
    limit: int = 50,
) -> MessageListResponse:
    """Get messages in a thread with cursor pagination."""
    db = get_database()

    thread = await db.get_tether_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    messages = await db.get_thread_messages(
        thread_id=thread_id,
        before=before,
        limit=limit,
    )

    return MessageListResponse(
        messages=[
            TetherMessageResponse(
                id=m["id"],
                thread_id=m["thread_id"],
                sender_name=m["sender_name"],
                sender_type=m["sender_type"],
                content=m["content"],
                message_type=m["message_type"],
                status=m["status"],
                reply_to=m.get("reply_to"),
                created_at=m.get("created_at"),
            )
            for m in messages
        ],
        count=len(messages),
    )


# =============================================================================
# Inbox Endpoints
# =============================================================================


@router.get("/inbox/{agent_id}", response_model=InboxResponse)
async def get_agent_inbox(
    agent_id: str,
    limit: int = 10,
) -> InboxResponse:
    """Get unread messages for an agent."""
    db = get_database()
    messages = await db.get_agent_inbox(agent_id, limit=limit)
    return InboxResponse(messages=messages, count=len(messages))


@router.post("/inbox/{agent_id}/read")
async def mark_inbox_read(
    agent_id: str,
    request: MarkReadRequest,
) -> dict:
    """Mark specific messages as read."""
    db = get_database()
    count = await db.mark_tether_messages_read(request.message_ids)
    return {"marked_read": count}


# =============================================================================
# Direct Send Shortcut
# =============================================================================


@router.post("/send", response_model=TetherMessageResponse)
async def send_direct_message(request: SendDirectRequest) -> TetherMessageResponse:
    """
    Send a message directly to an agent.

    Creates or reuses a user_agent thread automatically.
    Triggers Fluid Persona evaluation and a heartbeat pulse.
    """
    db = get_database()
    cache = get_cache()

    # Verify agent exists
    agent = await db.get_agent_state(request.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent_uuid = await db.get_agent_uuid(request.agent_id)
    if not agent_uuid:
        raise HTTPException(status_code=404, detail="Agent UUID not found")

    # Find or create a user_agent thread
    # Look for an existing active thread where this agent participates
    threads = await db.list_tether_threads(
        agent_id=request.agent_id,
        thread_type="user_agent",
        limit=1,
    )

    if threads:
        thread_id = threads[0]["id"]
    else:
        thread_id = await db.create_tether_thread(
            thread_type="user_agent",
            created_by=request.sender_name,
            subject=f"Conversation with {agent.name}",
        )
        await db.add_tether_participant(thread_id, request.agent_id)

    # Post the message
    msg_id = await db.post_tether_message(
        thread_id=thread_id,
        sender_type="user",
        sender_name=request.sender_name,
        content=request.content,
        message_type="chat",
        recipient_agent_id=agent_uuid,
    )

    if not msg_id:
        raise HTTPException(status_code=500, detail="Failed to send message")

    # Signal Redis inbox
    await cache.signal_tether_inbox(request.agent_id, msg_id)

    # Broadcast via WebSocket
    ws_manager = get_connection_manager()
    await ws_manager.broadcast_to_thread(
        thread_id,
        "TETHER_MESSAGE",
        {
            "id": msg_id,
            "thread_id": thread_id,
            "sender_name": request.sender_name,
            "sender_type": "user",
            "content": request.content,
            "message_type": "chat",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    # Fluid Persona evaluation
    try:
        identity_manager = get_identity_manager(db)
        current_spirit = agent.designation if agent else "Echo"
        await identity_manager.evaluate_and_sync(
            agent_id=request.agent_id,
            current_spirit=current_spirit,
            user_message=request.content,
        )
    except Exception as e:
        logger.warning(f"Fluid Persona evaluation failed: {e}")

    # Trigger heartbeat pulse
    heartbeat = get_heartbeat_service()
    try:
        await heartbeat.trigger_once(request.agent_id, user_message=request.content)
    except Exception as e:
        logger.warning(f"Heartbeat trigger failed: {e}")

    return TetherMessageResponse(
        id=msg_id,
        thread_id=thread_id,
        sender_name=request.sender_name,
        sender_type="user",
        content=request.content,
        message_type="chat",
        status="pending",
        created_at=datetime.now(timezone.utc),
    )
