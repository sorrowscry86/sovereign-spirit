"""
VoidCat RDC: Sovereign Middleware Service
==========================================
Version: 1.0.0
Author: Echo (E-01)
Date: 2026-01-23

This service acts as the central API gateway for Sovereign Spirit agents.
It provides:
- Agent management endpoints (/agent/{id}/*)
- Weaviate proxy with Valence Stripping
- Lifespan management for database connections
"""

import os
import json
import asyncio
import logging
from typing import Any, Dict
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import httpx
from fastapi import (
    FastAPI,
    Request,
    Header,
    HTTPException,
    Depends,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.middleware.valence_stripping import process_memory_batch, MemoryObject
from src.middleware.security import verify_api_key, check_rate_limit
from src.api.agents import router as agents_router
from src.api.graph import router as graph_router
from src.api.config import router as config_router
from src.core.database import get_database, StimuliRecord
from src.core.graph import get_graph
from src.core.heartbeat import get_heartbeat_service
from src.core.vector import get_vector_client
from src.core.cache import get_cache
from src.core.llm_client import shutdown_llm_client
from src.core.identity.manager import get_identity_manager
from src.core.socket_manager import get_connection_manager

# =============================================================================
# Configuration
# =============================================================================

WEAVIATE_URL = os.getenv("VOIDC_WEAVIATE_URL", "http://weaviate:8080")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Initialize logging
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    force=True,
)
logger = logging.getLogger("sovereign-middleware")

# =============================================================================
# Lifespan Management
# =============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle.

    Startup:
    - Initialize PostgreSQL connection
    - Initialize Neo4j connection

    Shutdown:
    - Close all database connections gracefully
    """
    logger.info("=== SOVEREIGN SPIRIT MIDDLEWARE STARTING ===")

    # Initialize database connections
    db = get_database()
    graph = get_graph()

    try:
        await db.initialize()
        logger.info("PostgreSQL connection established")
    except Exception as e:
        logger.error(f"PostgreSQL initialization failed: {e}")

    try:
        await graph.initialize()
        logger.info("Neo4j connection established")
    except Exception as e:
        logger.error(f"Neo4j initialization failed: {e}")

    # Initialize heartbeat service
    heartbeat = get_heartbeat_service()
    try:
        await heartbeat.start()
        logger.info(
            f"Heartbeat service started: {len(heartbeat.registered_agents)} agents"
        )
    except Exception as e:
        logger.error(f"Heartbeat initialization failed: {e}")

    # Initialize ngrok tunnel for remote access (if enabled)
    ngrok_tunnel = None
    ngrok_enabled = os.getenv("NGROK_ENABLED", "false").lower() == "true"
    if ngrok_enabled:
        try:
            from pyngrok import ngrok, conf

            # Configure ngrok (authtoken from env if available)
            authtoken = os.getenv("NGROK_AUTHTOKEN")
            if authtoken:
                conf.get_default().auth_token = authtoken

            # Start tunnel on port 8090
            ngrok_tunnel = ngrok.connect(8090, bind_tls=True)
            public_url = ngrok_tunnel.public_url

            logger.info(f"🌐 REMOTE ACCESS ENABLED: {public_url}")
            logger.info("📱 Use this URL in VoidCat Tether for remote connection")

            # Save to environment for other components
            os.environ["VOIDC_PUBLIC_URL"] = public_url

        except Exception as e:
            logger.warning(f"ngrok tunnel failed to start: {e}")
            logger.warning("Remote access unavailable - local network only")

    logger.info("===SOVEREIGN SPIRIT MIDDLEWARE ONLINE ===")

    yield  # Application runs here

    # Shutdown ngrok tunnel
    if ngrok_tunnel:
        try:
            ngrok.disconnect(ngrok_tunnel.public_url)
            logger.info("ngrok tunnel closed")
        except Exception as e:
            logger.warning(f"ngrok shutdown warning: {e}")

    # Stop heartbeat service
    await heartbeat.stop()

    # Cleanup
    logger.info("=== SOVEREIGN SPIRIT MIDDLEWARE SHUTTING DOWN ===")

    # Close all clients gracefully
    await db.close()
    logger.info("PostgreSQL connection closed")

    await graph.close()
    logger.info("Neo4j connection closed")

    # Close vector client (Weaviate)
    try:
        vector = get_vector_client()
        await vector.close()
        logger.info("Weaviate connection closed")
    except Exception as e:
        logger.warning(f"Weaviate shutdown warning: {e}")

    # Close cache client (Redis)
    try:
        cache = get_cache()
        await cache.close()
        logger.info("Redis connection closed")
    except Exception as e:
        logger.warning(f"Redis shutdown warning: {e}")

    # Close LLM client (httpx)
    try:
        await shutdown_llm_client()
        logger.info("LLM client closed")
    except Exception as e:
        logger.warning(f"LLM client shutdown warning: {e}")

    logger.info("=== SHUTDOWN COMPLETE ===")


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="VoidCat Sovereign Spirit",
    description="Autonomous AI Agent Operating System",
    version="1.0.0",
    lifespan=lifespan,
    openapi_url="/api/v1/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "VoidCat RDC",
        "url": "https://github.com/sorrowscry86/sovereign-spirit",
        "email": "SorrowsCry86@gmail.org",
    },
    license_info={
        "name": "MIT",
    },
    dependencies=[Depends(verify_api_key)],
)

# =============================================================================
# CORS Configuration
# =============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:8000",  # FastAPI server
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Security Middleware
# =============================================================================


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    """
    Apply security checks to all incoming requests.

    - Rate limiting
    - API key verification (if enabled)
    """
    # Check rate limit first
    await check_rate_limit(request)

    # Proceed with request
    response = await call_next(request)
    return response


# =============================================================================
# Core Endpoints
# =============================================================================

from pydantic import BaseModel
from typing import List, Optional


class LogEntry(BaseModel):
    timestamp: datetime
    agent_id: str
    thought_content: Optional[str] = None
    trigger: str


class LogResponse(BaseModel):
    logs: List[LogEntry]
    count: int


class PulseRequest(BaseModel):
    agent_id: Optional[str] = None
    action: str = "MUSE"


# =============================================================================
# API Routers
# =============================================================================

# Import and register API routers
from src.api import messages

app.include_router(messages.router)

# =============================================================================
# Inline API Endpoints (Legacy - to be migrated to routers)
# =============================================================================


@app.get("/api/logs/thoughts", response_model=LogResponse)
async def get_system_thoughts(limit: int = 50):
    """
    Get recent system-wide thoughts/logs.
    Used by the Scrying Glass dashboard and Mobile Tether.
    """
    db = get_database()
    # Filter for interesting actions
    logs = await db.get_system_logs(
        limit=limit, actions=["MUSE", "TASK", "ACT", "SLEEP"]
    )

    return LogResponse(
        logs=[
            LogEntry(
                timestamp=log["timestamp"],
                agent_id=log["agent_id"],
                thought_content=log.get("thought_content") or log.get("details"),
                trigger=log.get("trigger") or log.get("action"),
            )
            for log in logs
        ],
        count=len(logs),
    )


@app.post("/api/pulse/trigger")
async def trigger_pulse(request: PulseRequest):
    """
    Trigger a manual pulse (MUSE/ACT cycle).
    If agent_id is provided, triggers that agent.
    If not, triggers a system-wide pulse for all active agents.
    """
    service = get_heartbeat_service()
    triggered = []

    if request.agent_id:
        # Target specific
        await service.trigger_once(request.agent_id)
        triggered.append(request.agent_id)
    else:
        # Global pulse
        for agent_id in service.registered_agents:
            await service.trigger_once(agent_id)
            triggered.append(agent_id)

    return {
        "status": "triggered",
        "action": request.action,
        "agents": triggered,
        "timestamp": datetime.now(timezone.utc),
    }


@app.get("/health")
async def health_check():
    """
    Service health endpoint.

    Returns status of middleware and connection to Weaviate.
    """
    db = get_database()
    graph = get_graph()

    return {
        "status": "online",
        "version": "1.0.0",
        "proxy_target": WEAVIATE_URL,
        "database": "connected" if db._initialized else "disconnected",
        "graph": "connected" if graph._initialized else "disconnected",
    }


# =============================================================================
# Router Registration
# =============================================================================

app.include_router(agents_router, prefix="/agent")
app.include_router(graph_router)
app.include_router(config_router)


@app.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    """
    Real-time connection for The Throne (Dashboard 2.0).
    Broadcasts Spirit State, Logs, and Heartbeat events.
    """
    manager = get_connection_manager()
    await manager.connect(websocket)

    db_client = get_database()
    identity_mgr = get_identity_manager(db_client)
    heartbeat = get_heartbeat_service()

    # Construction of "Throne" Protocol
    update_task = None
    try:

        async def _build_all_agents_payload() -> dict:
            agents = await db_client.list_agents()
            now = datetime.now(timezone.utc)
            agent_list = []
            for agent in agents:
                created_at = agent.created_at
                if created_at is not None and created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=timezone.utc)
                uptime = (now - created_at).total_seconds() if created_at else 0
                agent_list.append(
                    {
                        "id": agent.name.lower(),
                        "name": agent.name,
                        "designation": agent.designation or "",
                        "mood": agent.current_mood or "Neutral",
                        "uptime": uptime,
                        "last_pulse": None,
                    }
                )
            return {"type": "STATE_UPDATE", "payload": {"agents": agent_list}}

        # Send initial multi-agent state packet
        initial = await _build_all_agents_payload()
        await websocket.send_json(initial)

        async def broadcast_updates() -> None:
            try:
                while True:
                    update = await _build_all_agents_payload()
                    await websocket.send_json(update)
                    await asyncio.sleep(2)
            except Exception as e:
                logger.warning(f"Broadcast loop stopped: {e}")

        # Start the broadcast loop in the background
        update_task = asyncio.create_task(broadcast_updates())

        while True:
            # Keep alive and listen for "God Mode" commands
            data_str = await websocket.receive_text()
            try:
                data = json.loads(data_str)
                cmd_type = data.get("type")
                payload = data.get("payload", {})

                logger.info(f"Dashboard command received: {cmd_type}")

                if cmd_type == "GOD_SYNC":
                    agent_id = payload.get("agent_id", "sovereign-001")
                    target = payload.get("spirit")
                    if target:
                        await identity_mgr.sync_agent_identity(agent_id, target)
                        logger.info(f"GOD_SYNC: {agent_id} synced to {target}")

                elif cmd_type == "GOD_MOOD":
                    agent_id = payload.get("agent_id", "sovereign-001")
                    mood = payload.get("mood")
                    if mood:
                        await db_client.update_agent_mood(agent_id, mood)
                        logger.info(f"GOD_MOOD: {agent_id} moved to {mood}")

                elif cmd_type == "GOD_STIMULI":
                    agent_id = payload.get("agent_id", "sovereign-001")
                    content = payload.get("content")
                    if content:
                        await db_client.record_stimuli(
                            StimuliRecord(
                                agent_id=agent_id, content=content, source="god_mode"
                            )
                        )
                        # Trigger pulse immediately
                        await heartbeat.trigger_once(agent_id)
                        logger.info(f"GOD_STIMULI: Injected to {agent_id}")

                # Echo back success or simple acknowledgement
                await websocket.send_json(
                    {"type": "CMD_ACK", "status": "processed", "cmd": cmd_type}
                )

            except json.JSONDecodeError:
                await websocket.send_text(f"Invalid JSON received: {data_str}")
            except Exception as e:
                logger.error(f"Error processing command {data_str}: {e}")
                await websocket.send_json(
                    {"type": "CMD_ACK", "status": "failed", "error": str(e)}
                )

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Dashboard WebSocket error: {e}")
        manager.disconnect(websocket)
    finally:
        if update_task is not None:
            update_task.cancel()


@app.post("/v1/graphql")
async def proxy_graphql(
    request: Request, x_agent_id: str = Header(..., alias="X-Agent-ID")
):
    """
    Proxy and sanitize GraphQL queries to Weaviate.

    This is the primary endpoint used by SillyTavern for memory retrieval.
    Applies Valence Stripping to ensure agent-specific memory isolation.
    """
    body = await request.json()

    logger.info(f"Intercepting GraphQL query for Agent: {x_agent_id}")

    async with httpx.AsyncClient() as client:
        try:
            # 1. Forward to real Weaviate
            response = await client.post(
                f"{WEAVIATE_URL}/v1/graphql", json=body, timeout=10.0
            )
            response.raise_for_status()
            data = response.json()

            # 2. Apply Valence Stripping to response
            sanitized_data = sanitize_weaviate_response(data, x_agent_id)

            return sanitized_data

        except httpx.HTTPStatusError as e:
            logger.error(f"Weaviate error: {e}")
            raise HTTPException(status_code=e.response.status_code, detail=str(e))
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise HTTPException(status_code=500, detail="Internal Middleware Error")


def sanitize_weaviate_response(data: Dict[str, Any], agent_id: str) -> Dict[str, Any]:
    """
    Traverses the Weaviate GraphQL response and applies valence stripping.

    Memory objects authored by other agents have their subjective_voice
    and emotional_valence stripped to prevent Soul Bleed.
    """
    # Check if response contains memory data
    if "data" not in data or "Get" not in data.get("data", {}):
        return data

    get_data = data["data"]["Get"]

    # Process Memory collection if present
    if "Memory" in get_data and isinstance(get_data["Memory"], list):
        raw_memories = []
        for item in get_data["Memory"]:
            try:
                memory = MemoryObject(
                    memory_id=item.get("memory_id", ""),
                    author_id=item.get("author_id", ""),
                    objective_fact=item.get("objective_fact", ""),
                    subjective_voice=item.get("subjective_voice", ""),
                    emotional_valence=float(item.get("emotional_valence", 0.0)),
                    timestamp=item.get("timestamp", ""),
                )
                raw_memories.append(memory)
            except Exception as e:
                logger.warning(f"Skipping malformed memory: {e}")
                continue

        # Apply valence stripping
        stripped = process_memory_batch(raw_memories, agent_id)

        # Replace with stripped version
        data["data"]["Get"]["Memory"] = [
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

    return data


# =============================================================================
# Static Files (The Throne)
# =============================================================================

# Ensure static directory exists
# Use absolute path to avoid CWD issues
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static"))
if not os.path.exists(static_dir):
    logger.warning(f"Static dir not found at {static_dir}, creating it")
    os.makedirs(static_dir)

# Mount the static directory to serve the Flutter Web app
# This must be mounted AFTER all API routes to avoid conflicts
# explicit root handler to ensure index.html is served
from fastapi.responses import FileResponse


@app.get("/")
async def serve_dashboard():
    index_path = os.path.join(static_dir, "index.html")
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="Index not found")
    return FileResponse(index_path)


app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8090)
