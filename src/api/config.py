"""
VoidCat RDC: Configuration API Router
========================================
Date: 2026-01-24
Author: Echo (E-01)

Provides configuration endpoints for:
- Bifrost Protocol: Hybrid inference mode management
- LLM Provider Configuration
- MCP Tool Registry
- Pantheon Roster
"""

import logging
import os
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Literal, Optional, Dict, List, Any
from src.core.llm_config import (
    load_config,
    save_config,
    apply_config_to_client,
    LLMConfigModel,
    ProviderConfigModel,
)
from src.core.llm_client import get_llm_client
from src.mcp.client import get_mcp_manager
from src.core.identity.evaluator import ContextEvaluator

logger = logging.getLogger("sovereign.api.config")

router = APIRouter(prefix="/config", tags=["Configuration"])

# =============================================================================
# Bifrost Protocol - Inference Configuration
# =============================================================================


class InferenceConfig(BaseModel):
    """Inference routing configuration"""

    mode: Literal["AUTO", "LOCAL", "CLOUD"] = "AUTO"


class InferenceStatus(BaseModel):
    """Current inference status"""

    mode: Literal["AUTO", "LOCAL", "CLOUD"]
    current_route: Literal["LOCAL", "CLOUD"]
    vram_usage: float = 0.0
    cloud_credits_remaining: int = 0  # Placeholder for future implementation


class MCPRegistryServerRequest(BaseModel):
    """Runtime MCP registry entry payload."""

    name: str
    command: str
    args: List[str] = Field(default_factory=list)
    security_tier: int = 1


# Global inference configuration (in-memory for now)
# TODO: Persist to PostgreSQL or Redis for multi-instance deployments
# _inference_config = InferenceConfig(mode="AUTO") # Replaced by client.inference_mode
# _current_route = "LOCAL"  # Tracks last routing decision # Replaced by client.current_route


@router.get("/inference")
async def get_inference_config() -> Dict[str, Any]:
    """
    Get current inference configuration and status.

    Returns mode, current route, and cloud health status.
    """
    client = get_llm_client()
    return {
        "mode": client.inference_mode,
        "current_route": client.current_route,
        "cloud_healthy": client.cloud_healthy,
        "last_cloud_failure": client.last_cloud_failure,
        "last_cloud_failure_at": (
            client.last_cloud_failure_at.isoformat()
            if client.last_cloud_failure_at
            else None
        ),
    }


@router.post("/inference")
async def update_inference_config(config: InferenceConfig):
    """
    Update inference routing mode.

    Args:
    - mode: "AUTO" (hybrid), "LOCAL" (privacy), or "CLOUD" (intelligence)

    Returns:
    - status: "updated"
    - mode: Confirmed new mode
    """
    client = get_llm_client()

    if config.mode not in ["AUTO", "LOCAL", "CLOUD"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode: {config.mode}. Must be AUTO, LOCAL, or CLOUD",
        )

    client.inference_mode = config.mode

    # Update current_route based on mode
    if config.mode == "CLOUD":
        client.current_route = "CLOUD"
    elif config.mode == "LOCAL":
        client.current_route = "LOCAL"
    # AUTO mode keeps last route (will be determined by routing logic)

    return {"status": "updated", "mode": config.mode}


@router.get("/inference/route")
async def get_current_route():
    """
    Get the current routing decision (LOCAL or CLOUD).

    This endpoint is called by the inference engine to determine
    where to send the next request based on the configured mode.
    """
    client = get_llm_client()
    return {"route": client.current_route, "mode": client.inference_mode}


# TODO: Implement these backend functions in src/inference/router.py:
# - route_request(prompt, intent) -> "LOCAL" | "CLOUD"
# - get_vram_usage() -> float
# - ValenceStripper.strip(prompt) -> str


# =============================================================================
# LLM Provider Configuration
# =============================================================================


@router.get("/llm", response_model=LLMConfigModel)
async def get_llm_config():
    """
    Get all LLM provider configurations from llm_providers.yaml.
    Masks API keys for security.
    """
    config = load_config()

    # Secure API keys for frontend display
    for name, provider in config.providers.items():
        if provider.api_key:
            # If it looks like an ENV variable, keep it, otherwise mask
            if not (
                provider.api_key.startswith("${") and provider.api_key.endswith("}")
            ):
                provider.api_key = "********"

    return config


@router.post("/llm")
async def update_llm_config(config: LLMConfigModel):
    """
    Update LLM provider configurations and save to llm_providers.yaml.
    """
    # Load current config to preserve API keys if masked ones are sent back
    current_config = load_config()

    for name, provider in config.providers.items():
        # If API key is masked (meaning user didn't change it), restore from current
        if provider.api_key == "********":
            if name in current_config.providers:
                provider.api_key = current_config.providers[name].api_key
            else:
                provider.api_key = None

    save_config(config)

    # Apply changes live so Bifrost updates take effect immediately.
    client = get_llm_client()
    apply_config_to_client(config, client)

    return {"status": "success", "message": "LLM configuration updated successfully"}


# =============================================================================
# LLM Provider Health Checks
# =============================================================================


@router.get("/llm/health")
async def get_llm_health() -> Dict[str, Any]:
    """
    Check the health status of all configured LLM providers.
    Returns a dict of provider_name -> {online: bool, type: str, model: str}.
    """
    client = get_llm_client()
    results: Dict[str, Any] = {}

    for name, provider in client.providers.items():
        try:
            online = await client.health_check(name)
        except Exception:
            online = False
        results[name] = {
            "online": online,
            "type": provider.provider_type.value,
            "model": provider.model,
            "endpoint": provider.endpoint,
        }

    return {"providers": results}


@router.get("/llm/health/{provider_name}")
async def get_llm_health_single(provider_name: str) -> Dict[str, Any]:
    """Check health of a single LLM provider."""
    client = get_llm_client()
    if provider_name not in client.providers:
        raise HTTPException(
            status_code=404, detail=f"Provider '{provider_name}' not found"
        )

    provider = client.providers[provider_name]
    try:
        online = await client.health_check(provider_name)
    except Exception:
        online = False

    return {
        "name": provider_name,
        "online": online,
        "type": provider.provider_type.value,
        "model": provider.model,
        "endpoint": provider.endpoint,
    }


@router.post("/llm/test/{provider_name}")
async def test_llm_provider(provider_name: str) -> Dict[str, Any]:
    """Send a test prompt to a specific provider and return the response."""
    client = get_llm_client()
    if provider_name not in client.providers:
        raise HTTPException(
            status_code=404, detail=f"Provider '{provider_name}' not found"
        )

    from src.core.llm_client import ChatMessage

    try:
        response = await client.complete(
            messages=[ChatMessage(role="user", content="Say hello in one sentence.")],
            provider_name=provider_name,
            use_fallback=False,
            max_tokens=50,
            temperature=0.7,
        )
        return {
            "success": True,
            "response": response.content,
            "model": response.model,
            "provider": response.provider,
            "tokens_used": response.tokens_used,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "provider": provider_name,
        }


@router.post("/llm/warm")
async def warm_local_provider() -> Dict[str, Any]:
    """Trigger LM Studio warm-up (load model for local fallback)."""
    client = get_llm_client()
    result = await client.warm_local_provider()
    return result


# =============================================================================
# MCP Tool Registry
# =============================================================================


@router.get("/tools")
async def get_tool_registry() -> Dict[str, Any]:
    """
    Return all available MCP tools grouped by server.
    Powers the Tools panel in the Throne.
    """
    mcp = get_mcp_manager()
    servers: Dict[str, List[Dict[str, str]]] = {}

    from src.mcp.config import MCP_SERVER_REGISTRY

    for tool in mcp.available_tools:
        server = tool.get("server", "unknown")
        if server not in servers:
            servers[server] = []
        security_tier = int(MCP_SERVER_REGISTRY.get(server, {}).get("security_tier", 1))
        servers[server].append(
            {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "security_tier": security_tier,
            }
        )

    return {
        "total_tools": len(mcp.available_tools),
        "servers": servers,
        "connected_servers": list(mcp.sessions.keys()),
    }


@router.post("/tools/connect/{server_name}")
async def connect_mcp_server(server_name: str) -> Dict[str, Any]:
    """Connect or reconnect an MCP server."""
    mcp = get_mcp_manager()
    if server_name in mcp.sessions:
        await mcp.disconnect_server(server_name)
    try:
        await mcp.connect_server(server_name)
        tool_count = len(
            [t for t in mcp.available_tools if t.get("server") == server_name]
        )
        return {
            "status": "connected",
            "server": server_name,
            "tools_loaded": tool_count,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect: {str(e)}")


@router.post("/tools/disconnect/{server_name}")
async def disconnect_mcp_server(server_name: str) -> Dict[str, Any]:
    """Disconnect an MCP server."""
    mcp = get_mcp_manager()
    if server_name not in mcp.sessions:
        raise HTTPException(
            status_code=404, detail=f"Server '{server_name}' not connected"
        )
    await mcp.disconnect_server(server_name)
    return {"status": "disconnected", "server": server_name}


@router.post("/tools/test/{server_name}/{tool_name}")
async def test_mcp_tool(
    server_name: str, tool_name: str, request: Request
) -> Dict[str, Any]:
    """Execute an MCP tool with provided arguments and return the result."""
    mcp = get_mcp_manager()
    if server_name not in mcp.sessions:
        raise HTTPException(
            status_code=404, detail=f"Server '{server_name}' not connected"
        )
    tool_exists = any(
        t["name"] == tool_name and t["server"] == server_name
        for t in mcp.available_tools
    )
    if not tool_exists:
        raise HTTPException(
            status_code=404, detail=f"Tool '{tool_name}' not found on '{server_name}'"
        )
    try:
        body = await request.json()
    except Exception:
        body = {}
    result = await mcp.execute_tool(server_name, tool_name, body)
    return {"tool": tool_name, "server": server_name, "result": result}


@router.get("/tools/registry")
async def get_mcp_registry() -> Dict[str, Any]:
    """Return the raw MCP server registry (available server definitions)."""
    from src.mcp.config import MCP_SERVER_REGISTRY

    mcp = get_mcp_manager()
    registry = {}
    for name, config in MCP_SERVER_REGISTRY.items():
        registry[name] = {
            "command": config["command"],
            "args": config["args"],
            "security_tier": int(config.get("security_tier", 1)),
            "connected": name in mcp.sessions,
        }
    return {"servers": registry}


@router.post("/tools/registry")
async def add_mcp_server_to_registry(payload: MCPRegistryServerRequest) -> Dict[str, Any]:
    """Add or update a server in the MCP registry (runtime only)."""
    from src.mcp.config import MCP_SERVER_REGISTRY

    name = payload.name
    command = payload.command
    args = payload.args or []
    security_tier = max(0, int(payload.security_tier))
    if not name or not command:
        raise HTTPException(status_code=400, detail="'name' and 'command' are required")
    MCP_SERVER_REGISTRY[name] = {
        "command": command,
        "args": args if isinstance(args, list) else args.split(),
        "env": {"PATH": os.environ.get("PATH", "")},
        "security_tier": security_tier,
    }
    return {
        "status": "added",
        "server": name,
        "security_tier": security_tier,
    }


# =============================================================================
# Agent Activity
# =============================================================================


@router.get("/agents/{agent_id}/activity")
async def get_agent_activity(agent_id: str, limit: int = 10) -> Dict[str, Any]:
    """
    Return recent heartbeat decisions and actions for an agent.
    Pulls from heartbeat_logs table.
    """
    from src.core.database import get_database
    from sqlalchemy import text

    db = get_database()
    async with db.session() as session:
        result = await session.execute(
            text("""
                SELECT h.action_taken, h.thought_content, h.created_at
                FROM heartbeat_logs h
                JOIN agents a ON h.agent_id = a.id
                WHERE a.name ILIKE :agent_id OR CAST(a.id AS TEXT) = :agent_id
                ORDER BY h.created_at DESC
                LIMIT :limit
            """),
            {"agent_id": agent_id, "limit": limit},
        )
        rows = result.mappings().all()

    return {
        "agent_id": agent_id,
        "activity": [
            {
                "action": row["action_taken"],
                "details": row.get("thought_content", ""),
                "timestamp": (
                    row["created_at"].isoformat() if row.get("created_at") else None
                ),
            }
            for row in rows
        ],
    }


# =============================================================================
# Pantheon Roster
# =============================================================================


@router.get("/agents/roster")
async def get_pantheon_roster() -> Dict[str, Any]:
    """
    Return the Pantheon roster used by the ContextEvaluator.
    Powers the agent overview in the Throne.
    """
    return {
        "roster": ContextEvaluator.PANTHEON,
        "count": len(ContextEvaluator.PANTHEON),
    }
