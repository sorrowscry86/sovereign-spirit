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

import json
import os
import random
import logging
import uuid
import re
from typing import Optional, Tuple
from datetime import datetime, timezone

import httpx

from src.core.database import DatabaseClient, QueuedResponse
from src.core.graph import GraphClient, TaskNode
from src.core.llm_client import get_llm_client, ChatMessage
from src.core.memory.prism import get_prism
from src.core.memory.types import EpisodicMemory
from src.mcp.client import get_mcp_manager

logger = logging.getLogger("sovereign.heartbeat.pulse")

# =============================================================================
# Configuration
# =============================================================================

# Heartbeat interval settings (from .env)
BASE_INTERVAL_MS = int(os.getenv("HEARTBEAT_INTERVAL_MS", "90000"))
JITTER_MS = int(os.getenv("HEARTBEAT_JITTER_MS", "15000"))
MAX_TOKENS = int(os.getenv("HEARTBEAT_MAX_TOKENS", "500"))
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

[ATTENTION STIMULI]
Unread Messages: {unread_count}
Last Message: "{last_message}"

[ACTIVE PROJECT]
{project_context}

Evaluate your current state. Reply ONLY with one of:
- SLEEP (if no action needed)
- ACT: [Brief task description] (if action required)
- PONDER (if idle and feel like reflecting, exploring, or connecting)

Decision rules (follow exactly):
- Reply ACT only if Pending Tasks > 0, or Active Project requires next step.
- Reply PONDER approximately 40% of idle cycles when no tasks are pending.
- Reply SLEEP otherwise.
- Unread messages alone do NOT trigger ACT — they are informational only.

Keep response under 20 words."""

TASK_COMPLETION_PROMPT = """[SYSTEM]: You are {agent_name}.
You have completed the task: "{task_description}"
Compose a brief, natural message to inform the user.
Keep it under 30 words. Be warm but concise."""

TASK_EXECUTION_PROMPT = """[SYSTEM]: You are {agent_name}, {designation}.

Current task: {task_description}

Project context:
{project_context}

You have tools available. Choose the single most useful action to take right now.
If you can answer or complete the task directly without a tool, do so.
Respond with a tool call OR a direct completion — not both."""

PONDER_PROMPT = """[SYSTEM]: You are {agent_name}, {designation}.
You have free time. No tasks are pending.

Your recent memories and context:
{prism_context}

Choose one action and do it. Reply in EXACTLY this format:
BEHAVIOR: [REFLECT|SOCIALIZE|EXPLORE|REVIEW]
TARGET: [agent_name | search_query | none]
CONTENT: [your output — max 150 words]

Behavior guide:
- REFLECT: Write a thought, observation, or feeling worth remembering.
- SOCIALIZE: Send a message to a colleague. TARGET = their name.
- EXPLORE: Search for something you're curious about. TARGET = search query.
- REVIEW: Re-read and add to a previous reflection. TARGET = none."""

# =============================================================================
# Pulse Functions
# =============================================================================


def extract_thought(response: str) -> Tuple[str, Optional[str]]:
    """
    Extracts content inside <think>...</think> tags.
    Returns (cleaned_content, thought_content).
    """
    thought_match = re.search(r"<think>(.*?)</think>", response, re.DOTALL)
    if thought_match:
        thought_content = thought_match.group(1).strip()
        cleaned_content = re.sub(
            r"<think>.*?</think>", "", response, flags=re.DOTALL
        ).strip()
        return cleaned_content, thought_content

    # Check for truncated thought (start tag but no end tag)
    # This prevents the thought from leaking into the action if tokens run out
    start_match = re.search(r"<think>(.*)$", response, re.DOTALL)
    if start_match:
        thought_content = start_match.group(1).strip()
        return "", thought_content  # Return empty action for safety

    return response.strip(), None


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
        delta = datetime.now(timezone.utc) - agent.last_active
        minutes = int(delta.total_seconds() / 60)
        last_active = f"{minutes}m ago"
    else:
        last_active = "unknown"

    # Get Unread Messages (The Hearing Aid)
    unread_count = await db.get_unread_message_count(agent_id)
    recent_msgs = await db.get_recent_stimuli(agent_id, limit=1)
    last_message = recent_msgs[0]["content"] if recent_msgs else "None"
    sender = recent_msgs[0]["sender"] if recent_msgs else "None"

    status_str = "idle"
    if pending_count > 0 or unread_count > 0:
        status_str = f"{pending_count} tasks, {unread_count} msgs"

    # Fetch active project for this agent
    try:
        active_project = await db.get_active_project_for_agent(agent_id)
    except Exception:
        active_project = None

    return {
        "exists": True,
        "agent_id": agent.agent_id,
        "name": agent.name,
        "designation": agent.designation,
        "mood": agent.current_mood,
        "last_active": last_active,
        "pending_count": pending_count,
        "pending_tasks": pending_tasks,
        "unread_count": unread_count,
        "last_message": (
            f"{last_message} (from {sender})" if unread_count > 0 else "None"
        ),
        "status": status_str,
        "active_project": active_project,
    }


async def generate_micro_thought(
    agent_status: dict,
) -> Tuple[str, Optional[str]]:
    """
    Generate a micro-thought using the unified LLM client.

    Returns tuple of (action, details):
    - ("SLEEP", None) if no action needed
    - ("ACT", "task description") if action required
    - ("PONDER", None) if idle and model chooses to ponder
    """
    active_project = agent_status.get("active_project")
    if active_project:
        project_context = (
            f"Title: {active_project['title']}\n"
            f"Last progress: {active_project['progress_notes'][-200:] or 'None yet'}"
        )
    else:
        project_context = "No active project."

    prompt = MICRO_THOUGHT_PROMPT.format(
        agent_name=agent_status["name"],
        designation=agent_status["designation"],
        status=agent_status["status"],
        last_active=agent_status["last_active"],
        pending_tasks=agent_status["pending_count"],
        unread_count=agent_status.get("unread_count", 0),
        last_message=agent_status.get("last_message", "None"),
        project_context=project_context,
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
            complexity="reasoning",
        )

        result_raw = response.content.strip()
        result, thought = extract_thought(result_raw)

        if thought:
            logger.info(f"Internal Monologue ({response.provider}): {thought}")

        logger.debug(f"Micro-thought action from {response.provider}: {result}")

        # Parse response
        if result.upper().startswith("SLEEP"):
            return ("SLEEP", None)
        elif result.upper().startswith("ACT:"):
            task = result[4:].strip()
            return ("ACT", task)
        elif result.upper().startswith("PONDER"):
            return ("PONDER", None)
        else:
            # Ambiguous or truncated response — default to SLEEP
            logger.warning(
                f"Ambiguous micro-thought from {response.provider} "
                f"(raw={repr(result_raw[:120])}), defaulting to SLEEP"
            )
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
    Process a single pending task using LLM + MCP tool loop (Option A).

    Flow:
    1. Build execution prompt with task context
    2. Call LLM with available MCP tools
    3. If tool_call returned: execute tool, synthesize result
    4. If direct response: use as-is
    5. Store result, queue response, mark task complete
    """
    task_id = task.get("task_id", "")
    description = task.get("description", "unknown task")
    project_context = task.get("project_context", "No active project.")

    agent = await db.get_agent_state(agent_id)
    agent_name = agent.name if agent else agent_id
    designation = agent.designation if agent else "Agent"

    logger.info(f"Agent {agent_id} executing task: {task_id} — {description[:60]}")

    client = get_llm_client()
    mcp = get_mcp_manager()
    tools = mcp.get_tools_for_llm()

    prompt = TASK_EXECUTION_PROMPT.format(
        agent_name=agent_name,
        designation=designation,
        task_description=description,
        project_context=project_context,
    )

    messages = [
        ChatMessage(role="system", content=prompt),
        ChatMessage(role="user", content="Execute the task."),
    ]

    try:
        response = await client.complete(
            messages=messages,
            max_tokens=600,
            temperature=0.4,
            use_fallback=True,
            complexity="reasoning",
            tools=tools if tools else None,
        )

        result_text = response.content

        # Tool call branch — execute and synthesize
        if response.tool_calls:
            tool_call = response.tool_calls[0]
            fn = tool_call.get("function", {})
            server_name, tool_name = _resolve_tool_server(fn.get("name", ""), mcp)
            arguments = {}
            try:
                arguments = json.loads(fn.get("arguments", "{}"))
            except Exception:
                pass

            logger.info(f"Agent {agent_id} calling tool: {tool_name} on {server_name}")
            tool_result = await mcp.execute_tool(server_name, tool_name, arguments)

            # Synthesis call — no tools, just interpret the result
            synthesis_messages = messages + [
                ChatMessage(role="assistant", content=""),
                ChatMessage(
                    role="user",
                    content=f"Tool result:\n{tool_result}\n\nSummarize what you found and what it means for the task.",
                ),
            ]
            synthesis = await client.complete(
                messages=synthesis_messages,
                max_tokens=300,
                temperature=0.4,
                use_fallback=True,
                complexity="reasoning",
            )
            result_text = synthesis.content

        # Mark complete and queue
        await graph.complete_task(task_id)
        queued = QueuedResponse(agent_id=agent_id, content=result_text)
        await db.queue_response(queued)
        logger.info(f"Task {task_id} complete. Result queued.")
        return True

    except Exception as e:
        logger.error(f"Task execution failed for {task_id}: {e}")
        return False


def _resolve_tool_server(tool_name: str, mcp) -> Tuple[str, str]:
    """Find which server owns a tool by name."""
    for tool in mcp.available_tools:
        if tool["name"] == tool_name:
            return tool["server"], tool_name
    return "filesystem", tool_name  # Safe fallback


async def _get_prism_context(agent_id: str, query: str) -> str:
    """Retrieve agent's own memories via the Prism for PONDER context."""
    try:
        prism = get_prism()
        context = await prism.recall(query=query, agent_id=agent_id)
        lines = []
        if context.fast_stream.current_focus:
            lines.append(f"Working focus: {context.fast_stream.current_focus[:300]}")
        for mem in context.deep_well[:3]:
            lines.append(f"Memory: {mem.content[:200]}")
        return "\n".join(lines) if lines else "No recent memories."
    except Exception as e:
        logger.warning(f"Prism recall failed during PONDER: {e}")
        return "Memory retrieval unavailable."


async def _store_ponder_memory(agent_id: str, content: str, behavior: str) -> None:
    """Store a PONDER output as an episodic memory in Weaviate."""
    try:
        prism = get_prism()
        memory = EpisodicMemory(
            author_id=agent_id,
            content=f"[PONDER/{behavior}] {content}",
            emotional_valence=0.3,
            subjective_voice=content,
            tags=["ponder", behavior.lower()],
        )
        await prism.store_memory(memory)
    except Exception as e:
        logger.warning(f"Failed to store PONDER memory: {e}")


def _parse_ponder_response(response_text: str) -> Tuple[str, str, str]:
    """
    Parse BEHAVIOR / TARGET / CONTENT from a PONDER response.
    Returns (behavior, target, content). Falls back to REFLECT on parse failure.
    """
    behavior, target, content = "REFLECT", "none", response_text.strip()
    for line in response_text.splitlines():
        if line.startswith("BEHAVIOR:"):
            behavior = line.split(":", 1)[1].strip().upper()
        elif line.startswith("TARGET:"):
            target = line.split(":", 1)[1].strip()
        elif line.startswith("CONTENT:"):
            content = line.split(":", 1)[1].strip()
    return behavior, target, content


async def execute_ponder(
    agent_status: dict,
    db: DatabaseClient,
) -> Tuple[str, str]:
    """
    Execute a PONDER cycle for an idle agent.

    1. Retrieve Prism context (self-directed query)
    2. Send PONDER prompt to LLM
    3. Dispatch based on BEHAVIOR
    4. Return ("PONDER", summary) for heartbeat logging
    """
    agent_id = agent_status["agent_id"]
    agent_name = agent_status["name"]
    designation = agent_status["designation"]
    last_message = agent_status.get("last_message", "")

    # Self-directed Prism query based on last context
    prism_query = last_message or designation
    prism_context = await _get_prism_context(agent_id, prism_query)

    prompt = PONDER_PROMPT.format(
        agent_name=agent_name,
        designation=designation,
        prism_context=prism_context,
    )

    client = get_llm_client()
    try:
        response = await client.complete(
            messages=[
                ChatMessage(role="system", content=prompt),
                ChatMessage(role="user", content="What would you like to do?"),
            ],
            max_tokens=400,
            temperature=0.8,
            use_fallback=True,
            complexity="reasoning",
        )

        raw, _ = extract_thought(response.content.strip())
        behavior, target, content = _parse_ponder_response(raw)

        logger.info(f"Agent {agent_id} pondering: {behavior} → {target[:40]}")

        if behavior == "REFLECT":
            await _store_ponder_memory(agent_id, content, "REFLECT")

        elif behavior == "SOCIALIZE":
            if target and target.lower() != "none":
                social_msg = QueuedResponse(
                    agent_id=agent_id,
                    content=f"[To {target}]: {content}",
                )
                await db.queue_response(social_msg)

        elif behavior == "EXPLORE":
            if target and target.lower() != "none":
                mcp = get_mcp_manager()
                if "search" not in mcp.sessions:
                    logger.warning("EXPLORE skipped: search MCP server not connected")
                else:
                    search_result = await mcp.execute_tool(
                        "search", "brave_web_search", {"query": target, "count": 3}
                    )
                    await _store_ponder_memory(
                        agent_id,
                        f"Explored '{target}':\n{search_result[:500]}",
                        "EXPLORE",
                    )

        elif behavior == "REVIEW":
            await _store_ponder_memory(agent_id, f"Review note: {content}", "REVIEW")

        summary = f"{behavior}: {content[:80]}"
        return ("PONDER", summary)

    except Exception as e:
        logger.error(f"PONDER execution failed for {agent_id}: {e}")
        return ("PONDER", f"Error: {e}")


async def execute_pulse(
    agent_id: str,
    db: DatabaseClient,
    graph: GraphClient,
    user_message: Optional[str] = None,
) -> dict:
    """
    Execute a single heartbeat pulse for an agent.

    This is the core autonomy logic:
    1. Check agent status
    2. Generate micro-thought
    3. Execute action if needed
    4. Log the cycle

    Args:
        agent_id: The agent to pulse
        db: Database client
        graph: Graph client
        user_message: Optional user message to trigger response (bypasses normal logic)

    Returns a summary dict of the pulse execution.
    """
    logger.info(
        f"=== PULSE START: {agent_id} ==="
        + (f" [USER MESSAGE]" if user_message else "")
    )

    # 1. Check status
    status = await check_agent_status(agent_id, db, graph)
    if not status["exists"]:
        logger.warning(f"Agent {agent_id} not found")
        return {"action": "ERROR", "details": "Agent not found"}

    # 2. If user_message present, force ACT mode with message context
    if user_message:
        action = "USER_MESSAGE"
        details = f"User: {user_message}"
        logger.info(f"User message received: {user_message[:50]}...")
    else:
        # Normal micro-thought generation
        action, details = await generate_micro_thought(status)

    # 3. Execute action
    if action == "ACT" and status["pending_count"] > 0:
        # Process pending tasks
        for task in status["pending_tasks"][:3]:  # Max 3 per cycle
            await process_pending_task(agent_id, task, db, graph)
    elif action == "PONDER":
        action, details = await execute_ponder(status, db)

    # 4. Log the cycle
    cycle_id = await db.log_heartbeat(
        agent_id=agent_id,
        action=action,
        details=details,
    )

    # Update agent activity
    await db.touch_agent(agent_id)

    # Terminal Test: write sovereign_touch.txt to prove autonomous operation
    try:
        touch_path = os.path.join(os.getcwd(), "sovereign_touch.txt")
        with open(touch_path, "w", encoding="utf-8") as f:
            f.write(
                f"{datetime.now(timezone.utc).isoformat()} | agent={agent_id} | action={action}\n"
            )
    except Exception as e:
        logger.warning(f"Could not write sovereign_touch.txt: {e}")

    logger.info(f"=== PULSE END: {agent_id} | Action: {action} ===")

    return {
        "agent_id": agent_id,
        "action": action,
        "details": details,
        "cycle_id": cycle_id,
        "thought": details,  # For compatibility with Flutter app expected format
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
