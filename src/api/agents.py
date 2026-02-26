"""
VoidCat RDC: Sovereign Spirit - Agent API Router
=================================================
Version: 1.0.0
Author: Echo (E-01)
Date: 2026-01-23

FastAPI router for the Agent Management API.
Implements the four core endpoints defined in PRODUCT_DEFINITION.md.
"""

import logging
import re
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends, Query, Path
from pydantic import BaseModel, Field

from src.core.database import (
    DatabaseClient,
    get_database,
    AgentState,
    StimuliRecord,
    QueuedResponse,
)
from src.core.graph import GraphClient, get_graph, TaskNode
from src.middleware.valence_stripping import process_memory_batch, MemoryObject
from src.middleware.security import sanitize_message_content
from src.core.identity.manager import get_identity_manager
from src.core.vector import get_vector_client
from src.adapters.voice_adapter import get_voice_adapter
from src.adapters.search_adapter import SearchAdapter
from src.adapters.search_adapter import SearchAdapter
from src.mcp.client import MCPManager
from src.core.sentinel import get_immune_system
from src.middleware.persona import get_persona_manager

logger = logging.getLogger("sovereign.api.agents")

router = APIRouter(prefix="/agent", tags=["agents"])

# =============================================================================
# Request/Response Models
# =============================================================================

class StimuliRequest(BaseModel):
    """Request body for sending stimuli to an agent."""
    message: str = Field(..., min_length=1, max_length=10000)
    source: str = Field(default="external", max_length=100)


class StimuliResponse(BaseModel):
    """Response after processing stimuli."""
    status: str
    message_id: str
    agent_id: str
    timestamp: datetime


class StateResponse(BaseModel):
    """Agent state response."""
    agent_id: str
    name: str
    designation: str
    current_mood: str
    last_active: Optional[datetime]
    pending_tasks: int
    queued_responses: List[Dict[str, Any]]


class AgentListResponse(BaseModel):
    """Response model for listing all agents."""
    agents: List[StateResponse]
    count: int



class MemoryQuery(BaseModel):
    """Query parameters for memory retrieval."""
    query: str = Field(default="", max_length=1000)
    limit: int = Field(default=10, ge=1, le=100)


class MemoryResponse(BaseModel):
    """Memory retrieval response with valence-stripped results."""
    agent_id: str
    memories: List[Dict[str, Any]]
    count: int


class CycleRequest(BaseModel):
    """Request body for manual heartbeat trigger."""
    force: bool = Field(default=False)


class CycleResponse(BaseModel):
    """Response after triggering a heartbeat cycle."""
    agent_id: str
    action: str
    details: Optional[str]
    cycle_id: str
    timestamp: datetime


class SyncRequest(BaseModel):
    """Request body for initiating a Spirit Sync."""
    target_spirit: str = Field(..., min_length=1, max_length=100)
    
    
class SyncResponse(BaseModel):
    """Response after a successful Spirit Sync."""
    status: str
    agent_id: str
    synced_to: str
    designation: str
    timestamp: datetime


# =============================================================================
# Validation
# =============================================================================

# Agent ID must be alphanumeric with underscores/hyphens, 1-50 chars
AGENT_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,50}$")


def validate_agent_id(agent_id: str) -> str:
    """
    Validate agent_id format to prevent injection attacks.

    Raises HTTPException if validation fails.
    """
    if not AGENT_ID_PATTERN.match(agent_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid agent_id format. Must be 1-50 alphanumeric characters, underscores, or hyphens."
        )
    return agent_id.lower()


# =============================================================================
# Dependency Injection
# =============================================================================

async def get_db() -> DatabaseClient:
    """Dependency to get database client."""
    db = get_database()
    if not db._initialized:
        await db.initialize()
    return db


async def get_graph_db() -> GraphClient:
    """Dependency to get graph client."""
    graph = get_graph()
    if not graph._initialized:
        await graph.initialize()
    return graph


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/", response_model=AgentListResponse)
async def list_agents(
    db: DatabaseClient = Depends(get_db),
    graph: GraphClient = Depends(get_graph_db),
):
    """
    List all available sovereign agents.
    
    Used by the dashboard to populate the agent selector.
    """
    # Get all agents from DB
    agents = await db.list_agents()
    
    response_list = []
    for agent in agents:
        # Get pending tasks for each (could be optimized with batch query)
        pending_tasks = await graph.get_pending_tasks_count(agent.agent_id)
        
        # Get queued responses
        queued = await db.get_queued_responses(agent.agent_id)
        
        response_list.append(StateResponse(
            agent_id=agent.agent_id,
            name=agent.name,
            designation=agent.designation,
            current_mood=agent.current_mood,
            last_active=agent.last_active,
            pending_tasks=pending_tasks,
            queued_responses=queued,
        ))
    
    return AgentListResponse(
        agents=response_list,
        count=len(response_list),
    )


@router.post("/{agent_id}/stimuli", response_model=StimuliResponse)
async def process_stimuli(
    agent_id: str = Path(..., min_length=1, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$"),
    request: StimuliRequest = None,
    db: DatabaseClient = Depends(get_db),
):
    """
    Process incoming stimuli (messages) to an agent.

    Records the message in the database and updates agent activity.
    """
    # Validate and normalize agent_id
    agent_id = validate_agent_id(agent_id)

    # Verify agent exists
    agent = await db.get_agent_state(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

    # Sanitize message content to prevent XSS/injection
    sanitized_message = sanitize_message_content(request.message)

    # Record stimuli with sanitized content
    stimuli = StimuliRecord(
        agent_id=agent_id,
        content=sanitized_message,
        source=request.source,
    )
    message_id = await db.record_stimuli(stimuli)
    
    # PHASE IV: Fluid Persona Shift
    try:
        persona_mgr = get_persona_manager(db)
        await persona_mgr.analyze_and_shift(agent_id, sanitized_message)
    except Exception as e:
        logger.warning(f"Persona shift failed: {e}")

    # Touch agent (update last_active)
    await db.touch_agent(agent_id)
    
    logger.info(f"Processed stimuli for agent {agent_id}: message_id={message_id}")
    
    return StimuliResponse(
        status="received",
        message_id=str(message_id),
        agent_id=agent_id,
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/{agent_id}/state", response_model=StateResponse)
async def get_agent_state(
    agent_id: str = Path(..., min_length=1, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$"),
    db: DatabaseClient = Depends(get_db),
    graph: GraphClient = Depends(get_graph_db),
):
    """
    Get the current state of an agent.

    Returns mood, last activity, pending tasks, and queued responses.
    """
    # Validate and normalize agent_id
    agent_id = validate_agent_id(agent_id)

    # Get agent state from PostgreSQL
    agent = await db.get_agent_state(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    
    # Get pending tasks from Neo4j
    pending_tasks = await graph.get_pending_tasks_count(agent_id)
    
    # Get queued responses
    queued = await db.get_queued_responses(agent_id)
    
    return StateResponse(
        agent_id=agent.agent_id,
        name=agent.name,
        designation=agent.designation,
        current_mood=agent.current_mood,
        last_active=agent.last_active,
        pending_tasks=pending_tasks,
        queued_responses=queued,
    )


@router.get("/{agent_id}/memories", response_model=MemoryResponse)
async def get_agent_memories(
    agent_id: str = Path(..., min_length=1, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$"),
    query: str = Query(default="", max_length=1000),
    limit: int = Query(default=10, ge=1, le=100),
    db: DatabaseClient = Depends(get_db),
):
    """
    Retrieve context memories for an agent.

    Applies Valence Stripping to ensure agent-specific memory isolation.
    Foreign memories have subjective_voice and emotional_valence stripped.
    """
    # Validate and normalize agent_id
    agent_id = validate_agent_id(agent_id)

    # Verify agent exists
    agent = await db.get_agent_state(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    
    # Query Weaviate for vector memories
    vector = get_vector_client()
    if query:
        raw_dicts = await vector.search(query, agent_id, limit)
        raw_memories = [
            MemoryObject(
                memory_id=d["memory_id"],
                author_id=d["author_id"],
                objective_fact=d["content"],
                subjective_voice=d["subjective_voice"],
                emotional_valence=d["emotional_valence"],
                timestamp=d["timestamp"],
            )
            for d in raw_dicts
        ]
    else:
        raw_memories = []
    
    # Apply valence stripping
    stripped = process_memory_batch(raw_memories, agent_id)
    
    # Convert to dicts for response
    memories = [
        {
            "memory_id": m.memory_id,
            "author_id": m.author_id,
            "objective_fact": m.objective_fact,
            "subjective_voice": m.subjective_voice,
            "emotional_valence": m.emotional_valence,
            "timestamp": m.timestamp,
        }
        for m in stripped
    ]
    
    return MemoryResponse(
        agent_id=agent_id,
        memories=memories,
        count=len(memories),
    )


@router.post("/{agent_id}/sync", response_model=SyncResponse)
async def trigger_spirit_sync(
    agent_id: str = Path(..., min_length=1, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$"),
    request: SyncRequest = None,
    db: DatabaseClient = Depends(get_db),
):
    """
    Manually trigger a Spirit Sync for an agent body.

    Allows an agent to manifest the DNA/Identity of another spirit.
    """
    # Validate and normalize agent_id
    agent_id = validate_agent_id(agent_id)

    manager = get_identity_manager(db)
    updated_state = await manager.sync_agent_identity(agent_id, request.target_spirit)
    
    if not updated_state:
        raise HTTPException(
            status_code=404, 
            detail=f"Sync failed: Target spirit '{request.target_spirit}' not found."
        )

    # Auditory Feedback
    voice = get_voice_adapter()
    voice.speak(f"Spirit synchronization complete. I am now {updated_state.name}.", persona=updated_state.name.lower())
        
    # Broadcast via WebSocket
    from src.core.socket_manager import get_connection_manager
    ws_manager = get_connection_manager()
    await ws_manager.broadcast("SYNC_UPDATE", {
        "agent_id": agent_id,
        "synced_to": updated_state.name,
        "designation": updated_state.designation,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return SyncResponse(
        status="synchronized",
        agent_id=agent_id,
        synced_to=updated_state.name,
        designation=updated_state.designation,
        timestamp=datetime.now(timezone.utc),
    )


@router.post("/{agent_id}/cycle", response_model=CycleResponse)
async def trigger_heartbeat_cycle(
    agent_id: str = Path(..., min_length=1, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$"),
    request: CycleRequest = CycleRequest(),
    db: DatabaseClient = Depends(get_db),
    graph: GraphClient = Depends(get_graph_db),
):
    """
    Manually trigger a heartbeat cycle for an agent.

    This simulates what happens during autonomous background operation.
    """
    # Validate and normalize agent_id
    agent_id = validate_agent_id(agent_id)

    # Verify agent exists
    agent = await db.get_agent_state(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    
    # Check for pending tasks
    pending_count = await graph.get_pending_tasks_count(agent_id)
    
    # Determine action
    if pending_count > 0:
        action = "ACT"
        details = f"Processing {pending_count} pending task(s)"
    else:
        action = "SLEEP"
        details = "No pending tasks. Entering idle state."
    
    # Log heartbeat
    cycle_id = await db.log_heartbeat(
        agent_id=agent_id,
        action=action,
        details=details,
    )
    
    # Update agent activity
    await db.touch_agent(agent_id)
    
    logger.info(f"Heartbeat cycle for {agent_id}: {action}")

    # Auditory Feedback (if acting)
    if action == "ACT":
        voice = get_voice_adapter()
        voice.speak(f"Alert. I am attending to my duties: {details}", persona=agent_id.lower())

    # Broadcast via WebSocket
    from src.core.socket_manager import get_connection_manager
    manager = get_connection_manager()
    await manager.broadcast("HEARTBEAT", {
        "agent_id": agent_id,
        "action": action,
        "thought": details,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return CycleResponse(
        agent_id=agent_id,
        action=action,
        details=details,
        cycle_id=str(cycle_id),
        timestamp=datetime.now(timezone.utc),
    )
