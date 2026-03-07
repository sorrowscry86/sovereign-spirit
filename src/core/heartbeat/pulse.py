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
import asyncio
import time
from typing import Optional, Tuple
from datetime import datetime, timezone

import httpx

from src.core.database import DatabaseClient, QueuedResponse
from src.core.graph import GraphClient, TaskNode
from src.core.llm_client import get_llm_client, ChatMessage
from src.core.memory.prism import get_prism
from src.core.memory.types import EpisodicMemory
from src.core.cache import get_cache
from src.core.socket_manager import get_connection_manager
from src.mcp.client import get_mcp_manager
from src.mcp.config import MCP_SERVER_REGISTRY
from src.core.inference.prompts import build_system_prompt

logger = logging.getLogger("sovereign.heartbeat.pulse")

# =============================================================================
# Configuration
# =============================================================================

# Heartbeat interval settings (from .env)
BASE_INTERVAL_MS = int(os.getenv("HEARTBEAT_INTERVAL_MS", "90000"))
JITTER_MS = int(os.getenv("HEARTBEAT_JITTER_MS", "15000"))
MAX_TOKENS = int(os.getenv("HEARTBEAT_MAX_TOKENS", "500"))
TEMPERATURE = float(os.getenv("HEARTBEAT_TEMPERATURE", "0.6"))
TOOL_APPROVAL_MODE = os.getenv("TOOL_APPROVAL_MODE", "auto").lower()
TOOL_APPROVAL_TTL_SECONDS = int(os.getenv("TOOL_APPROVAL_TTL_SECONDS", "300"))
TOOL_SENSITIVE_TIER_MIN = int(os.getenv("TOOL_SENSITIVE_TIER_MIN", "2"))

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

[INBOX — {inbox_count} messages]
{inbox_summary}

[ACTIVE PROJECT]
{project_context}

Evaluate your current state. Reply ONLY with one of:
- SLEEP (if no action needed)
- ACT: [Brief task description] (if action required)
- ACT: RESPOND (if Inbox contains messages from User that need a reply)
- PONDER (if idle and feel like reflecting, exploring, or connecting)

Decision rules (follow exactly):
- Reply ACT: RESPOND if Inbox contains messages from User.
- Reply ACT only if Pending Tasks > 0, or Active Project requires next step.
- Reply PONDER if Inbox contains messages from other agents, or idle with ~40% chance.
- Reply SLEEP otherwise.

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

INBOX_RESPONSE_PROMPT = """[SYSTEM]: You are {agent_name}, {designation}.
You have received messages in your inbox. Respond naturally and helpfully.

Messages:
{inbox_messages}

Respond to the most important message. Be warm, concise, and in-character.
Keep response under 150 words.

IMPORTANT OUTPUT FORMAT (MANDATORY):
- If you need to reason or plan, wrap that internal monologue in <think>...</think>.
- Put the user-visible reply in <final>...</final>.
- Never claim you searched files, checked configs, or ran tools unless the result is present in this thread/tool context.
"""

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


def sanitize_visible_reply(response: str) -> str:
    """
    Produce the user-visible reply text from model output.

    Priority order:
    1) <final>...</final> payload if present
    2) response with <think>...</think> removed
    3) defensive pruning of obvious planning/meta scaffolding
    """
    final_match = re.search(r"<final>(.*?)</final>", response, re.DOTALL | re.IGNORECASE)
    if final_match:
        visible = final_match.group(1).strip()
    else:
        visible, _ = extract_thought(response)

    # Remove any residual XML-style control tags that should never be shown.
    visible = re.sub(r"</?(think|final)>", "", visible, flags=re.IGNORECASE).strip()
    if not visible:
        return ""

    meta_prefixes = (
        "okay",
        "let me",
        "the user",
        "i need to",
        "first",
        "second",
        "third",
        "wait",
        "actually",
        "i should",
        "i think",
        "now,",
        "check",
        "word count",
        "tools available",
        "response should",
        "as ",
    )

    meta_regex = re.compile(
        r"\b(i need to|let me|the user|i should|i think|word count|"
        r"tools available|response should|internal monologue|"
        r"this is within my domain|i don't have|i do not have|"
        r"i can report|my response should)\b",
        re.IGNORECASE,
    )

    kept_lines = []
    for raw_line in visible.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        # Remove planning-heavy sentences even when mixed into a single line.
        sentences = re.split(r"(?<=[.!?])\s+", line)
        clean_sentences = []
        for sentence in sentences:
            s = sentence.strip()
            if not s:
                continue
            lowered = s.lower()
            if lowered.startswith(meta_prefixes):
                continue
            if meta_regex.search(s):
                continue
            clean_sentences.append(s)

        if clean_sentences:
            kept_lines.append(" ".join(clean_sentences))

    if kept_lines:
        return "\n".join(kept_lines).strip()

    # Last-resort fallback: keep only the tail sentence fragment.
    tail = re.split(r"(?<=[.!?])\s+", visible.strip())
    return tail[-1].strip() if tail else ""


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

    # Get Tether Inbox (replaces legacy stimuli polling)
    inbox = await db.get_agent_inbox(agent_id, limit=5)
    inbox_count = len(inbox)

    # Build structured inbox summary for MUSE prompt
    inbox_lines = []
    for msg in inbox[:3]:
        sender_label = msg["sender_type"].upper()
        inbox_lines.append(
            f"- [{sender_label} {msg['sender_name']}]: {msg['content'][:80]}"
        )
    inbox_summary = "\n".join(inbox_lines) if inbox_lines else "No messages."

    # Legacy compatibility: extract last message info
    last_message = inbox[0]["content"] if inbox else "None"
    sender = inbox[0]["sender_name"] if inbox else "None"

    status_str = "idle"
    if pending_count > 0 or inbox_count > 0:
        status_str = f"{pending_count} tasks, {inbox_count} msgs"

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
        "inbox": inbox,
        "inbox_count": inbox_count,
        "inbox_summary": inbox_summary,
        "unread_count": inbox_count,
        "last_message": (
            f"{last_message} (from {sender})" if inbox_count > 0 else "None"
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
        inbox_count=agent_status.get("inbox_count", 0),
        inbox_summary=agent_status.get("inbox_summary", "No messages."),
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
            chain_id = f"task-{task_id or uuid.uuid4()}"
            chain_step = 1
            tool_call = response.tool_calls[0]
            fn = tool_call.get("function", {})
            server_name, tool_name = _resolve_tool_server(fn.get("name", ""), mcp)
            arguments = {}
            try:
                arguments = json.loads(fn.get("arguments", "{}"))
            except Exception:
                pass

            logger.info(f"Agent {agent_id} calling tool: {tool_name} on {server_name}")
            await _emit_tool_use_event(
                db=db,
                thread_id="",
                agent_id=agent_id,
                chain_id=chain_id,
                chain_step=chain_step,
                chain_status="running",
                phase="requested",
                tool_name=tool_name,
                tool_server=server_name,
                args_preview=_preview(arguments),
                result_preview="",
                duration_ms=None,
            )
            await _emit_tool_use_event(
                db=db,
                thread_id="",
                agent_id=agent_id,
                chain_id=chain_id,
                chain_step=chain_step,
                chain_status="running",
                phase="executing",
                tool_name=tool_name,
                tool_server=server_name,
                args_preview=_preview(arguments),
                result_preview="",
                duration_ms=None,
            )
            started_at = time.monotonic()
            tool_result = await mcp.execute_tool(server_name, tool_name, arguments)
            duration_ms = int((time.monotonic() - started_at) * 1000)
            await _emit_tool_use_event(
                db=db,
                thread_id="",
                agent_id=agent_id,
                chain_id=chain_id,
                chain_step=chain_step,
                chain_status="running",
                phase="completed",
                tool_name=tool_name,
                tool_server=server_name,
                args_preview=_preview(arguments),
                result_preview=_preview(tool_result),
                duration_ms=duration_ms,
            )

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


def _preview(value: object, limit: int = 500) -> str:
    """Create bounded previews for audit records and websocket payloads."""
    text = str(value) if value is not None else ""
    return text if len(text) <= limit else f"{text[:limit]}..."


def _tool_security_tier(server_name: str) -> int:
    """Resolve security tier from MCP server registry."""
    entry = MCP_SERVER_REGISTRY.get(server_name, {})
    try:
        return int(entry.get("security_tier", 1))
    except Exception:
        return 1


def _tool_requires_approval(security_tier: int) -> bool:
    """Decide if a tool invocation requires human approval."""
    mode = TOOL_APPROVAL_MODE
    if mode == "ask":
        return True
    if mode == "deny_sensitive_only":
        return security_tier >= TOOL_SENSITIVE_TIER_MIN
    return False


async def _record_tool_event(
    db: DatabaseClient,
    event_id: str,
    agent_id: str,
    thread_id: str,
    chain_id: str,
    chain_step: int,
    chain_status: str,
    phase: str,
    tool_name: Optional[str],
    tool_server: Optional[str],
    args_preview: Optional[str],
    result_preview: Optional[str],
    duration_ms: Optional[int],
) -> None:
    """Persist tool/reply chain lifecycle event. Never blocks main flow on failure."""
    try:
        await db.log_tool_execution_event(
            event_id=event_id,
            agent_id=agent_id,
            thread_id=thread_id,
            chain_id=chain_id,
            chain_step=chain_step,
            chain_status=chain_status,
            phase=phase,
            tool_name=tool_name,
            tool_server=tool_server,
            args_preview=args_preview,
            result_preview=result_preview,
            duration_ms=duration_ms,
        )
    except Exception as e:
        logger.warning(f"Tool lifecycle audit write failed: {e}")


async def _emit_reply_chain_event(
    db: DatabaseClient,
    thread_id: str,
    agent_id: str,
    chain_id: str,
    chain_step: int,
    chain_status: str,
    parent_message_id: Optional[str],
    details: str,
) -> None:
    """Broadcast a reply-chain transition and persist it to audit storage."""
    event_id = str(uuid.uuid4())
    payload = {
        "event_id": event_id,
        "agent_id": agent_id,
        "thread_id": thread_id,
        "chain_id": chain_id,
        "chain_step": chain_step,
        "chain_status": chain_status,
        "parent_message_id": parent_message_id,
        "details": _preview(details),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    ws_manager = get_connection_manager()
    await ws_manager.broadcast_to_thread(thread_id, "REPLY_CHAIN_EVENT", payload)
    await _record_tool_event(
        db=db,
        event_id=event_id,
        agent_id=agent_id,
        thread_id=thread_id,
        chain_id=chain_id,
        chain_step=chain_step,
        chain_status=chain_status,
        phase="chain_state",
        tool_name=None,
        tool_server=None,
        args_preview=None,
        result_preview=_preview(details),
        duration_ms=None,
    )


async def _emit_tool_use_event(
    db: DatabaseClient,
    thread_id: str,
    agent_id: str,
    chain_id: str,
    chain_step: int,
    chain_status: str,
    phase: str,
    tool_name: str,
    tool_server: str,
    args_preview: str,
    result_preview: str,
    duration_ms: Optional[int],
) -> None:
    """Broadcast a tool lifecycle event and persist it to audit storage."""
    event_id = str(uuid.uuid4())
    payload = {
        "event_id": event_id,
        "agent_id": agent_id,
        "thread_id": thread_id,
        "chain_id": chain_id,
        "chain_step": chain_step,
        "chain_status": chain_status,
        "phase": phase,
        "tool": tool_name,
        "server": tool_server,
        "args_preview": _preview(args_preview),
        "result_preview": _preview(result_preview),
        "duration_ms": duration_ms,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    ws_manager = get_connection_manager()
    await ws_manager.broadcast_to_thread(thread_id, "TOOL_USE_EVENT", payload)
    await _record_tool_event(
        db=db,
        event_id=event_id,
        agent_id=agent_id,
        thread_id=thread_id,
        chain_id=chain_id,
        chain_step=chain_step,
        chain_status=chain_status,
        phase=phase,
        tool_name=tool_name,
        tool_server=tool_server,
        args_preview=_preview(args_preview),
        result_preview=_preview(result_preview),
        duration_ms=duration_ms,
    )


async def _await_tool_approval(
    db: DatabaseClient,
    thread_id: str,
    agent_id: str,
    chain_id: str,
    chain_step: int,
    parent_message_id: Optional[str],
    tool_name: str,
    tool_server: str,
    arguments: dict,
) -> Tuple[bool, str]:
    """Wait for human approval with TTL. Timeout defaults to deny."""
    cache = get_cache()
    approval_key = f"tool_approval:{chain_id}"
    await cache.set(approval_key, "waiting", expire=TOOL_APPROVAL_TTL_SECONDS)

    ws_manager = get_connection_manager()
    await ws_manager.broadcast_to_thread(
        thread_id,
        "TOOL_USE_APPROVAL_REQUIRED",
        {
            "chain_id": chain_id,
            "chain_step": chain_step,
            "agent_id": agent_id,
            "thread_id": thread_id,
            "tool": tool_name,
            "server": tool_server,
            "args_preview": _preview(arguments),
            "ttl_seconds": TOOL_APPROVAL_TTL_SECONDS,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )

    await _emit_reply_chain_event(
        db=db,
        thread_id=thread_id,
        agent_id=agent_id,
        chain_id=chain_id,
        chain_step=chain_step,
        chain_status="waiting_approval",
        parent_message_id=parent_message_id,
        details=f"Awaiting approval for {tool_server}.{tool_name}",
    )

    start = time.monotonic()
    while (time.monotonic() - start) < TOOL_APPROVAL_TTL_SECONDS:
        decision = await cache.get(approval_key)
        if isinstance(decision, bytes):
            decision = decision.decode("utf-8", errors="ignore")

        if decision in {"approved", "resumed"}:
            return True, str(decision)
        if decision in {"denied", "cancelled"}:
            return False, f"TOOL_USE_DENY({decision})"

        await asyncio.sleep(1)

    await cache.set(approval_key, "timeout", expire=60)
    return False, "TOOL_USE_DENY(timeout)"


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


async def process_inbox_response(
    agent_status: dict,
    db: DatabaseClient,
) -> Tuple[str, str]:
    """
    Process inbox messages and generate a response via LLM.

    Reads unread messages, generates a reply, writes it back as a
    tether_messages row, and broadcasts via WebSocket.
    """
    agent_id = agent_status["agent_id"]
    agent_name = agent_status["name"]
    designation = agent_status["designation"]
    inbox = agent_status.get("inbox", [])

    if not inbox:
        return ("ACT", "No messages to respond to")

    # Build message context for the LLM
    inbox_lines = []
    for msg in inbox[:5]:
        sender_label = msg["sender_type"].upper()
        inbox_lines.append(f"[{sender_label} {msg['sender_name']}]: {msg['content']}")
    inbox_text = "\n".join(inbox_lines)

    target_msg = inbox[0]
    thread_id = target_msg["thread_id"]
    parent_message_id = target_msg["id"]
    chain_id = str(uuid.uuid4())
    chain_step = 1

    # Pull recent thread history so the model continues the current conversation
    # instead of resetting into generic greeting behavior.
    thread_history = await db.get_thread_messages(thread_id=thread_id, limit=12)
    thread_history = list(reversed(thread_history))

    agent_state = await db.get_agent_state(agent_id)
    if agent_state and agent_state.system_prompt:
        persona_prompt = agent_state.system_prompt
    else:
        traits = agent_state.traits if agent_state else {}
        persona_prompt = build_system_prompt(
            agent_name=agent_name,
            designation=designation,
            archetype=traits.get("archetype", designation),
            traits={
                "big_five": traits.get("big_five", {}),
                "expertise_tags": (agent_state.expertise_tags if agent_state else []),
                "behavior_modes": (agent_state.behavior_modes if agent_state else []),
            },
        )

    prompt = INBOX_RESPONSE_PROMPT.format(
        agent_name=agent_name,
        designation=designation,
        inbox_messages=inbox_text,
    )

    system_prompt = (
        f"{persona_prompt}\n\n"
        "### RESPONSE CONTINUITY (MANDATORY)\n"
        "1. Continue the active thread context below. Do not restart with a fresh greeting unless the user explicitly starts over.\n"
        "2. Prioritize unresolved points from the latest turns.\n"
        "3. If peer coordination is needed, acknowledge Pantheon peers as internal collaborators.\n\n"
        f"{prompt}"
    )

    if agent_name.strip().lower() == "beatrice":
        system_prompt += (
            "\n\n### BEATRICE END-CADENCE (MANDATORY)\n"
            "End key declarative lines with \"I suppose.\" or \"In fact.\" while maintaining natural rhythm."
        )

    client = get_llm_client()
    mcp = get_mcp_manager()
    tools = mcp.get_tools_for_llm()

    messages = [ChatMessage(role="system", content=system_prompt)]

    for msg in thread_history:
        sender_type = (msg.get("sender_type") or "").lower()
        sender_name = msg.get("sender_name") or "Unknown"
        content = (msg.get("content") or "").strip()
        if not content:
            continue

        if sender_type == "agent" and sender_name.lower() == agent_name.lower():
            role = "assistant"
        else:
            role = "user"

        messages.append(ChatMessage(role=role, content=f"{sender_name}: {content}"))

    messages.append(
        ChatMessage(
            role="user",
            content="Respond to the latest pending message with continuity and in-character precision.",
        )
    )

    try:
        await _emit_reply_chain_event(
            db=db,
            thread_id=thread_id,
            agent_id=agent_id,
            chain_id=chain_id,
            chain_step=chain_step,
            chain_status="queued",
            parent_message_id=parent_message_id,
            details="Inbox response queued for execution",
        )
        await _emit_reply_chain_event(
            db=db,
            thread_id=thread_id,
            agent_id=agent_id,
            chain_id=chain_id,
            chain_step=chain_step,
            chain_status="running",
            parent_message_id=parent_message_id,
            details="Generating first response turn",
        )

        response = await client.complete(
            messages=messages,
            max_tokens=400,
            temperature=0.6,
            use_fallback=True,
            complexity="reasoning",
            tools=tools if tools else None,
        )

        reply_text = response.content.strip()

        if response.tool_calls:
            chain_step += 1
            tool_call = response.tool_calls[0]
            fn = tool_call.get("function", {})
            server_name, tool_name = _resolve_tool_server(fn.get("name", ""), mcp)
            arguments = {}
            try:
                arguments = json.loads(fn.get("arguments", "{}"))
            except Exception:
                arguments = {}

            logger.info(f"Agent {agent_id} inbox tool call: {tool_name} on {server_name}")
            await _emit_reply_chain_event(
                db=db,
                thread_id=thread_id,
                agent_id=agent_id,
                chain_id=chain_id,
                chain_step=chain_step,
                chain_status="waiting_tool",
                parent_message_id=parent_message_id,
                details=f"Preparing tool call {server_name}.{tool_name}",
            )
            await _emit_tool_use_event(
                db=db,
                thread_id=thread_id,
                agent_id=agent_id,
                chain_id=chain_id,
                chain_step=chain_step,
                chain_status="waiting_tool",
                phase="requested",
                tool_name=tool_name,
                tool_server=server_name,
                args_preview=_preview(arguments),
                result_preview="",
                duration_ms=None,
            )

            security_tier = _tool_security_tier(server_name)
            approved = True
            deny_reason = ""
            if _tool_requires_approval(security_tier):
                approved, deny_reason = await _await_tool_approval(
                    db=db,
                    thread_id=thread_id,
                    agent_id=agent_id,
                    chain_id=chain_id,
                    chain_step=chain_step,
                    parent_message_id=parent_message_id,
                    tool_name=tool_name,
                    tool_server=server_name,
                    arguments=arguments,
                )

            if not approved:
                await _emit_tool_use_event(
                    db=db,
                    thread_id=thread_id,
                    agent_id=agent_id,
                    chain_id=chain_id,
                    chain_step=chain_step,
                    chain_status="failed",
                    phase="failed",
                    tool_name=tool_name,
                    tool_server=server_name,
                    args_preview=_preview(arguments),
                    result_preview=f"Tool denied ({deny_reason})",
                    duration_ms=None,
                )
                await _emit_reply_chain_event(
                    db=db,
                    thread_id=thread_id,
                    agent_id=agent_id,
                    chain_id=chain_id,
                    chain_step=chain_step,
                    chain_status="failed",
                    parent_message_id=parent_message_id,
                    details=f"Tool execution denied ({deny_reason})",
                )
                reply_text = (
                    "Tool execution was denied by approval policy "
                    f"({deny_reason}). I can proceed with a non-tool response if you want."
                )
            else:
                await _emit_tool_use_event(
                    db=db,
                    thread_id=thread_id,
                    agent_id=agent_id,
                    chain_id=chain_id,
                    chain_step=chain_step,
                    chain_status="running",
                    phase="executing",
                    tool_name=tool_name,
                    tool_server=server_name,
                    args_preview=_preview(arguments),
                    result_preview="",
                    duration_ms=None,
                )
                started_at = time.monotonic()
                tool_result = await mcp.execute_tool(server_name, tool_name, arguments)
                duration_ms = int((time.monotonic() - started_at) * 1000)
                await _emit_tool_use_event(
                    db=db,
                    thread_id=thread_id,
                    agent_id=agent_id,
                    chain_id=chain_id,
                    chain_step=chain_step,
                    chain_status="running",
                    phase="completed",
                    tool_name=tool_name,
                    tool_server=server_name,
                    args_preview=_preview(arguments),
                    result_preview=_preview(tool_result),
                    duration_ms=duration_ms,
                )

                # Map tool output directly into the active context window before the next turn.
                messages.append(
                    ChatMessage(
                        role="user",
                        content=(
                            "Tool output injected into active context window:\n"
                            f"{server_name}.{tool_name} result:\n{tool_result}"
                        ),
                    )
                )

                synthesis_messages = messages + [
                    ChatMessage(role="assistant", content=""),
                    ChatMessage(
                        role="user",
                        content=(
                            "Tool result:\n"
                            f"{tool_result}\n\n"
                            "Now craft the final in-thread reply. Maintain persona and continuity. "
                            "Output user-visible text in <final>...</final>."
                        ),
                    ),
                ]
                synthesis = await client.complete(
                    messages=synthesis_messages,
                    max_tokens=300,
                    temperature=0.5,
                    use_fallback=True,
                    complexity="reasoning",
                )
                reply_text = synthesis.content.strip()

        reply_text = sanitize_visible_reply(reply_text)
        if not reply_text:
            reply_text = "Acknowledged. I will proceed with the current thread context."

        # Resolve agent UUID for sender
        agent_uuid = await db.get_agent_uuid(agent_id)

        # Determine recipient: if the sender was a user, recipient is None (broadcast to thread)
        # If the sender was an agent, recipient is the sender's agent UUID
        recipient_uuid = None
        if target_msg["sender_type"] == "agent":
            recipient_uuid = await db.get_agent_uuid(target_msg["sender_name"])

        # Post the reply to the tether thread
        msg_id = await db.post_tether_message(
            thread_id=thread_id,
            sender_type="agent",
            sender_name=agent_name,
            content=reply_text,
            message_type="chat",
            sender_agent_id=agent_uuid,
            recipient_agent_id=recipient_uuid,
            reply_to=target_msg["id"],
        )

        # Signal recipient inbox if it's an agent
        if recipient_uuid:
            cache = get_cache()
            await cache.signal_tether_inbox(target_msg["sender_name"], msg_id)

        # Broadcast via WebSocket
        ws_manager = get_connection_manager()
        await ws_manager.broadcast_to_thread(
            thread_id,
            "TETHER_MESSAGE",
            {
                "id": msg_id,
                "thread_id": thread_id,
                "sender_name": agent_name,
                "sender_type": "agent",
                "content": reply_text,
                "message_type": "chat",
                "reply_to": target_msg["id"],
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        await _emit_reply_chain_event(
            db=db,
            thread_id=thread_id,
            agent_id=agent_id,
            chain_id=chain_id,
            chain_step=chain_step,
            chain_status="completed",
            parent_message_id=parent_message_id,
            details="Reply chain completed and posted to thread",
        )

        # Mark processed messages as read
        processed_ids = [msg["id"] for msg in inbox]
        await db.mark_tether_messages_read(processed_ids)

        # Also clear Redis inbox signals
        cache = get_cache()
        await cache.clear_tether_inbox_signals(agent_id)

        logger.info(f"Agent {agent_id} responded to inbox ({len(inbox)} msgs)")
        return ("ACT", f"RESPOND: {reply_text[:80]}")

    except Exception as e:
        try:
            await _emit_reply_chain_event(
                db=db,
                thread_id=thread_id,
                agent_id=agent_id,
                chain_id=chain_id,
                chain_step=chain_step,
                chain_status="failed",
                parent_message_id=parent_message_id,
                details=f"Inbox response failure: {e}",
            )
        except Exception:
            pass
        logger.error(f"Inbox response failed for {agent_id}: {e}")
        return ("ACT", f"RESPOND error: {e}")


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

        raw = sanitize_visible_reply(response.content.strip())
        behavior, target, content = _parse_ponder_response(raw)

        # Defensive cleanup before persistence/broadcast.
        content = sanitize_visible_reply(content)

        logger.info(f"Agent {agent_id} pondering: {behavior} → {target[:40]}")

        if behavior == "REFLECT":
            await _store_ponder_memory(agent_id, content, "REFLECT")

        elif behavior == "SOCIALIZE":
            if target and target.lower() != "none":
                target_agent = await db.get_agent_state(target)
                if target_agent:
                    target_uuid = await db.get_agent_uuid(target)
                    agent_uuid = await db.get_agent_uuid(agent_id)
                    thread_id = await db.get_or_create_thread(
                        agent_id, target, "agent_agent"
                    )
                    msg_id = await db.post_tether_message(
                        thread_id=thread_id,
                        sender_type="agent",
                        sender_name=agent_name,
                        content=content,
                        message_type="ponder_social",
                        sender_agent_id=agent_uuid,
                        recipient_agent_id=target_uuid,
                    )
                    # Signal Redis inbox for target agent
                    cache = get_cache()
                    await cache.signal_tether_inbox(target, msg_id)
                    # Broadcast via WebSocket
                    ws_manager = get_connection_manager()
                    await ws_manager.broadcast_to_thread(
                        thread_id,
                        "TETHER_MESSAGE",
                        {
                            "id": msg_id,
                            "thread_id": thread_id,
                            "sender_name": agent_name,
                            "sender_type": "agent",
                            "content": content,
                            "message_type": "ponder_social",
                            "created_at": datetime.now(timezone.utc).isoformat(),
                        },
                    )
                    logger.info(f"Agent {agent_id} sent tether message to {target}")
                else:
                    logger.warning(
                        f"SOCIALIZE target '{target}' not found in agent registry"
                    )

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


async def _record_no_inbox_telemetry(
    agent_id: str,
    route: str,
    outcome: str,
) -> None:
    """Persist no-inbox routing telemetry for observability and tuning."""
    try:
        cache = get_cache()
        hash_name = "telemetry:no_inbox"
        route_key = route.lower()
        outcome_key = outcome.lower()

        await cache.h_incr(hash_name, "total", 1)
        await cache.h_incr(hash_name, f"agent:{agent_id}", 1)
        await cache.h_incr(hash_name, f"route:{route_key}", 1)
        await cache.h_incr(hash_name, f"route:{route_key}:outcome:{outcome_key}", 1)

        logger.info(
            f"NO_INBOX_TELEMETRY agent={agent_id} route={route_key} outcome={outcome_key}"
        )
    except Exception as e:
        logger.warning(f"No inbox telemetry write failed: {e}")


def _build_idle_explore_query(agent_status: dict) -> str:
    """Build a concise exploration query from current agent context."""
    active_project = agent_status.get("active_project")
    if active_project and active_project.get("title"):
        return (
            f"recent developments and practical methods for "
            f"{active_project['title']}"
        )

    designation = agent_status.get("designation") or "autonomous ai agents"
    return f"latest best practices for {designation}"


async def route_no_inbox_autonomy(
    agent_status: dict,
    db: DatabaseClient,
) -> Tuple[str, str]:
    """
    Route ACT/RESPOND-empty outcomes to useful autonomous work.

    Priority:
    1. EXPLORE via Perplexity MCP (fallback to Brave search MCP)
    2. REVIEW via Prism recall + memory note
    3. PONDER via existing free-time behavior engine
    4. SLEEP only if all routes are unavailable or fail
    """
    agent_id = agent_status["agent_id"]
    route_order = ["EXPLORE", "REVIEW", "PONDER"]

    # Add variety while preserving required route coverage.
    random.shuffle(route_order)

    for route in route_order:
        if route == "EXPLORE":
            query = _build_idle_explore_query(agent_status)
            mcp = get_mcp_manager()

            try:
                if "perplexity" in mcp.sessions:
                    result = await mcp.execute_tool(
                        "perplexity",
                        "perplexity_search",
                        {"query": query},
                    )
                    await _store_ponder_memory(
                        agent_id,
                        f"Idle EXPLORE via perplexity_search ('{query}'):\n"
                        f"{result[:800]}",
                        "EXPLORE",
                    )
                    await _record_no_inbox_telemetry(agent_id, "EXPLORE", "success")
                    return ("ACT", f"EXPLORE (Perplexity): {query[:90]}")

                if "search" in mcp.sessions:
                    result = await mcp.execute_tool(
                        "search",
                        "brave_web_search",
                        {"query": query, "count": 3},
                    )
                    await _store_ponder_memory(
                        agent_id,
                        f"Idle EXPLORE via brave_web_search ('{query}'):\n"
                        f"{result[:800]}",
                        "EXPLORE",
                    )
                    await _record_no_inbox_telemetry(agent_id, "EXPLORE", "success")
                    return ("ACT", f"EXPLORE (Search): {query[:90]}")

                logger.info(
                    "No inbox autonomy EXPLORE skipped: no search MCP sessions"
                )
                await _record_no_inbox_telemetry(agent_id, "EXPLORE", "skipped")
            except Exception as e:
                logger.warning(f"No inbox autonomy EXPLORE failed: {e}")
                await _record_no_inbox_telemetry(agent_id, "EXPLORE", "failed")

        elif route == "REVIEW":
            try:
                recall = await _get_prism_context(
                    agent_id,
                    "recent reflections, unresolved patterns, and useful next steps",
                )
                if recall and recall != "Memory retrieval unavailable.":
                    note = (
                        "Review sweep complete. Most relevant context:\n"
                        f"{recall[:600]}"
                    )
                    await _store_ponder_memory(agent_id, note, "REVIEW")
                    await _record_no_inbox_telemetry(agent_id, "REVIEW", "success")
                    return ("ACT", "REVIEW: revisited recent context")
            except Exception as e:
                logger.warning(f"No inbox autonomy REVIEW failed: {e}")
                await _record_no_inbox_telemetry(agent_id, "REVIEW", "failed")

        elif route == "PONDER":
            try:
                _, ponder_details = await execute_ponder(agent_status, db)
                if ponder_details and not ponder_details.startswith("Error:"):
                    await _record_no_inbox_telemetry(agent_id, "PONDER", "success")
                    return ("ACT", f"PONDER: {ponder_details[:90]}")
            except Exception as e:
                logger.warning(f"No inbox autonomy PONDER failed: {e}")
                await _record_no_inbox_telemetry(agent_id, "PONDER", "failed")

    await _record_no_inbox_telemetry(agent_id, "SLEEP", "fallback")
    return ("SLEEP", "No inbox and no autonomous route available")


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

    # 2. If user_message present, force ACT: RESPOND mode
    if user_message:
        action = "ACT"
        details = "RESPOND"
        logger.info(f"User message received: {user_message[:50]}...")
    else:
        # Normal micro-thought generation
        action, details = await generate_micro_thought(status)

    # 3. Execute action
    if action == "ACT" and details and details.strip().startswith("RESPOND"):
        # Respond to inbox messages
        action, details = await process_inbox_response(status, db)

        # If no inbox work exists, route into autonomous idle tasks before sleep.
        if details and details.strip().startswith("No messages to respond to"):
            action, details = await route_no_inbox_autonomy(status, db)
    elif action == "ACT" and status["pending_count"] > 0:
        # Process pending tasks
        for task in status["pending_tasks"][:3]:  # Max 3 per cycle
            await process_pending_task(agent_id, task, db, graph)
    elif action == "ACT":
        # ACT requested, but no inbox-response or pending task path was viable.
        # Route to autonomous branch before any fallback to SLEEP.
        action, details = await route_no_inbox_autonomy(status, db)
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
