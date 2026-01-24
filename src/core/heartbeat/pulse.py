"""
VoidCat RDC: Sovereign Spirit Core - The Pulse
===============================================
Version: 1.0.0
Author: Echo (E-01)
Date: 2026-01-23

The Heartbeat Pulse: Core logic for autonomous background agency.
This is Pillar 2 of the Sovereign Architecture - the ability to
process thoughts without being spoken to.
"""

import os
import random
import logging
import uuid
from typing import Optional, Tuple
from datetime import datetime

import httpx

from src.core.database import DatabaseClient, QueuedResponse
from src.core.graph import GraphClient, TaskNode
from src.core.llm_client import get_llm_client, ChatMessage

logger = logging.getLogger("sovereign.heartbeat.pulse")

# =============================================================================
# Configuration
# =============================================================================

# Heartbeat interval settings (from .env)
BASE_INTERVAL_MS = int(os.getenv("HEARTBEAT_INTERVAL_MS", "90000"))
JITTER_MS = int(os.getenv("HEARTBEAT_JITTER_MS", "15000"))
MAX_TOKENS = int(os.getenv("HEARTBEAT_MAX_TOKENS", "75"))
TEMPERATURE = float(os.getenv("HEARTBEAT_TEMPERATURE", "0.6"))

# Ollama configuration (deprecated - now uses llm_client)
# These are kept for backwards compatibility if llm_config.yaml doesn't exist
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral:7b-instruct-v0.2-q4_K_M")

# =============================================================================
# Prompt Templates
# =============================================================================

MICRO_THOUGHT_PROMPT = """[SYSTEM]: You are {agent_name}, designation: {designation}.
Current Status: {status}
User Last Active: {last_active}
Pending Tasks: {pending_tasks}

Evaluate your current state. Reply ONLY with one of:
- SLEEP (if no action needed)
- ACT: [Brief task description] (if action required)

Keep response under 20 words."""

TASK_COMPLETION_PROMPT = """[SYSTEM]: You are {agent_name}.
You have completed the task: "{task_description}"
Compose a brief, natural message to inform the user.
Keep it under 30 words. Be warm but concise."""

# =============================================================================
# Pulse Functions
# =============================================================================

def calculate_next_interval() -> float:
    """
    Calculate the next heartbeat interval with jitter.
    
    Returns interval in seconds.
    """
    base = BASE_INTERVAL_MS / 1000.0
    jitter = (random.random() * 2 - 1) * (JITTER_MS / 1000.0)
    return max(30.0, base + jitter)  # Minimum 30 seconds


async def check_agent_status(
    agent_id: str,
    db: DatabaseClient,
    graph: GraphClient,
) -> dict:
    """
    Gather current status information for an agent.
    
    Returns a dict with status details for prompt construction.
    """
    # Get agent state
    agent = await db.get_agent_state(agent_id)
    if not agent:
        return {"exists": False}
    
    # Get pending tasks
    pending_count = await graph.get_pending_tasks_count(agent_id)
    pending_tasks = await graph.get_agent_tasks(agent_id, status="pending")
    
    # Calculate last active
    if agent.last_active:
        delta = datetime.utcnow() - agent.last_active
        minutes = int(delta.total_seconds() / 60)
        last_active = f"{minutes}m ago"
    else:
        last_active = "unknown"
    
    return {
        "exists": True,
        "agent_id": agent.agent_id,
        "name": agent.name,
        "designation": agent.designation,
        "mood": agent.current_mood,
        "last_active": last_active,
        "pending_count": pending_count,
        "pending_tasks": pending_tasks,
        "status": "idle" if pending_count == 0 else f"{pending_count} pending task(s)",
    }


async def generate_micro_thought(
    agent_status: dict,
) -> Tuple[str, Optional[str]]:
    """
    Generate a micro-thought using the unified LLM client.
    
    Returns tuple of (action, details):
    - ("SLEEP", None) if no action needed
    - ("ACT", "task description") if action required
    """
    prompt = MICRO_THOUGHT_PROMPT.format(
        agent_name=agent_status["name"],
        designation=agent_status["designation"],
        status=agent_status["status"],
        last_active=agent_status["last_active"],
        pending_tasks=agent_status["pending_count"],
    )
    
    try:
        client = get_llm_client()
        messages = [
            ChatMessage(role="system", content=prompt),
            ChatMessage(role="user", content="Evaluate your current state."),
        ]
        
        response = await client.complete(
            messages=messages,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            use_fallback=True,
        )
        
        result = response.content.strip()
        logger.debug(f"Micro-thought response from {response.provider}: {result}")
        
        # Parse response
        if result.upper().startswith("SLEEP"):
            return ("SLEEP", None)
        elif result.upper().startswith("ACT:"):
            task = result[4:].strip()
            return ("ACT", task)
        else:
            # Ambiguous response, default to sleep
            logger.warning(f"Ambiguous micro-thought: {result}")
            return ("SLEEP", result)
                
    except Exception as e:
        logger.error(f"Micro-thought generation failed: {e}")
        return ("SLEEP", f"Error: {e}")


async def process_pending_task(
    agent_id: str,
    task: dict,
    db: DatabaseClient,
    graph: GraphClient,
) -> bool:
    """
    Process a single pending task.
    
    For now, this marks tasks as complete and queues a response.
    In future, this would delegate to specific task handlers.
    """
    task_id = task.get("task_id", "")
    description = task.get("description", "unknown task")
    
    logger.info(f"Agent {agent_id} processing task: {task_id}")
    
    # Mark task as complete
    success = await graph.complete_task(task_id)
    
    if success:
        # Queue a response message
        response = QueuedResponse(
            agent_id=agent_id,
            content=f"I have attended to: {description}",
        )
        await db.queue_response(response)
        logger.info(f"Task {task_id} completed, response queued")
    
    return success


async def execute_pulse(
    agent_id: str,
    db: DatabaseClient,
    graph: GraphClient,
) -> dict:
    """
    Execute a single heartbeat pulse for an agent.
    
    This is the core autonomy logic:
    1. Check agent status
    2. Generate micro-thought
    3. Execute action if needed
    4. Log the cycle
    
    Returns a summary dict of the pulse execution.
    """
    logger.info(f"=== PULSE START: {agent_id} ===")
    
    # 1. Check status
    status = await check_agent_status(agent_id, db, graph)
    if not status["exists"]:
        logger.warning(f"Agent {agent_id} not found")
        return {"action": "ERROR", "details": "Agent not found"}
    
    # 2. Generate micro-thought
    action, details = await generate_micro_thought(status)
    
    # 3. Execute action
    if action == "ACT" and status["pending_count"] > 0:
        # Process pending tasks
        for task in status["pending_tasks"][:3]:  # Max 3 per cycle
            await process_pending_task(agent_id, task, db, graph)
    
    # 4. Log the cycle
    cycle_id = await db.log_heartbeat(
        agent_id=agent_id,
        action=action,
        details=details,
    )
    
    # Update agent activity
    await db.touch_agent(agent_id)
    
    logger.info(f"=== PULSE END: {agent_id} | Action: {action} ===")
    
    return {
        "agent_id": agent_id,
        "action": action,
        "details": details,
        "cycle_id": cycle_id,
        "timestamp": datetime.utcnow().isoformat(),
    }
