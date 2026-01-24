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
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Query
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
from src.core.identity.manager import get_identity_manager

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

@router.post("/{agent_id}/stimuli", response_model=StimuliResponse)
async def process_stimuli(
    agent_id: str,
    request: StimuliRequest,
    db: DatabaseClient = Depends(get_db),
):
    """
    Process incoming stimuli (messages) to an agent.
    
    Records the message in the database and updates agent activity.
    """
    # Verify agent exists
    agent = await db.get_agent_state(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    
    # Record stimuli
    stimuli = StimuliRecord(
        agent_id=agent_id,
        content=request.message,
        source=request.source,
    )
    message_id = await db.record_stimuli(stimuli)
    
    # Touch agent (update last_active)
    await db.touch_agent(agent_id)
    
    logger.info(f"Processed stimuli for agent {agent_id}: message_id={message_id}")
    
    return StimuliResponse(
        status="received",
        message_id=str(message_id),
        agent_id=agent_id,
        timestamp=datetime.utcnow(),
    )


@router.get("/{agent_id}/state", response_model=StateResponse)
async def get_agent_state(
    agent_id: str,
    db: DatabaseClient = Depends(get_db),
    graph: GraphClient = Depends(get_graph_db),
):
    """
    Get the current state of an agent.
    
    Returns mood, last activity, pending tasks, and queued responses.
    """
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
    agent_id: str,
    query: str = Query(default="", max_length=1000),
    limit: int = Query(default=10, ge=1, le=100),
    db: DatabaseClient = Depends(get_db),
):
    """
    Retrieve context memories for an agent.
    
    Applies Valence Stripping to ensure agent-specific memory isolation.
    Foreign memories have subjective_voice and emotional_valence stripped.
    """
    # Verify agent exists
    agent = await db.get_agent_state(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    
    # TODO: Query Weaviate for vector memories
    # For now, return a placeholder showing the valence stripping demo
    raw_memories = [
        MemoryObject(
            memory_id="demo_001",
            author_id="beatrice",
            objective_fact="The user requested plant watering reminder.",
            subjective_voice="I find this task delightfully simple.",
            emotional_valence=0.7,
            timestamp=datetime.utcnow().isoformat(),
        ),
    ]
    
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
    agent_id: str,
    request: SyncRequest,
    db: DatabaseClient = Depends(get_db),
):
    """
    Manually trigger a Spirit Sync for an agent body.
    
    Allows an agent to manifest the DNA/Identity of another spirit.
    """
    manager = get_identity_manager(db)
    updated_state = await manager.sync_agent_identity(agent_id, request.target_spirit)
    
    if not updated_state:
        raise HTTPException(
            status_code=404, 
            detail=f"Sync failed: Target spirit '{request.target_spirit}' not found."
        )
        
    # Broadcast via WebSocket
    from src.core.socket_manager import get_connection_manager
    ws_manager = get_connection_manager()
    await ws_manager.broadcast("SYNC_UPDATE", {
        "agent_id": agent_id,
        "synced_to": updated_state.name,
        "designation": updated_state.designation,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    return SyncResponse(
        status="synchronized",
        agent_id=agent_id,
        synced_to=updated_state.name,
        designation=updated_state.designation,
        timestamp=datetime.utcnow(),
    )


@router.post("/{agent_id}/cycle", response_model=CycleResponse)
async def trigger_heartbeat_cycle(
    agent_id: str,
    request: CycleRequest = CycleRequest(),
    db: DatabaseClient = Depends(get_db),
    graph: GraphClient = Depends(get_graph_db),
):
    """
    Manually trigger a heartbeat cycle for an agent.
    
    This simulates what happens during autonomous background operation.
    """
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

    # Broadcast via WebSocket
    from src.core.socket_manager import get_connection_manager
    manager = get_connection_manager()
    await manager.broadcast("HEARTBEAT", {
        "agent_id": agent_id,
        "action": action,
        "thought": details,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    return CycleResponse(
        agent_id=agent_id,
        action=action,
        details=details,
        cycle_id=str(cycle_id),
        timestamp=datetime.utcnow(),
    )
