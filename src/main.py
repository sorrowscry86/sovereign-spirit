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
import logging
from typing import Any, Dict
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.middleware.valence_stripping import process_memory_batch, MemoryObject
from src.middleware.security import verify_api_key, check_rate_limit
from src.api.agents import router as agents_router
from src.api.graph import router as graph_router
from src.api.config import router as config_router
from src.core.database import get_database
from src.core.graph import get_graph
from src.core.heartbeat import get_heartbeat_service
from src.core.vector import get_vector_client
from src.core.cache import get_cache
from src.core.llm_client import shutdown_llm_client

# =============================================================================
# Configuration
# =============================================================================

WEAVIATE_URL = os.getenv("VOIDC_WEAVIATE_URL", "http://weaviate:8080")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Initialize logging
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
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
        logger.info(f"Heartbeat service started: {len(heartbeat.registered_agents)} agents")
    except Exception as e:
        logger.error(f"Heartbeat initialization failed: {e}")
    
    logger.info("=== SOVEREIGN SPIRIT MIDDLEWARE ONLINE ===")
    
    yield  # Application runs here
    
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

    # Verify API key (if enabled)
    await verify_api_key(request)

    # Proceed with request
    response = await call_next(request)
    return response


# Mount routers
app.include_router(agents_router)

# =============================================================================
# Core Endpoints
# =============================================================================

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

from src.core.socket_manager import get_connection_manager
from fastapi import WebSocket, WebSocketDisconnect

# =============================================================================
# Router Registration
# =============================================================================

app.include_router(agents_router, prefix="/agent")
app.include_router(graph_router)
app.include_router(config_router)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Real-time nervous system connection."""
    manager = get_connection_manager()
    await manager.connect(websocket)
    try:
        while True:
            # Keep alive / listen for ping
            data = await websocket.receive_text()
            # Echo back for latency checks
            await websocket.send_text(f"echo: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.post("/v1/graphql")
async def proxy_graphql(
    request: Request,
    x_agent_id: str = Header(..., alias="X-Agent-ID")
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
                f"{WEAVIATE_URL}/v1/graphql",
                json=body,
                timeout=10.0
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
# Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

