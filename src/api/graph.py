"""
VoidCat RDC: Sovereign Spirit - Graph API Router
=================================================
Version: 1.0.0
Author: Ryuzu (The Sculptor) under Echo's direction
Date: 2026-01-24

FastAPI router for Graph/Neo4j endpoints.
Provides task graph visualization data.
"""

import logging
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.core.graph import GraphClient, get_graph

logger = logging.getLogger("sovereign.api.graph")

router = APIRouter(prefix="/graph", tags=["graph"])

# =============================================================================
# Response Models
# =============================================================================

class GraphNode(BaseModel):
    """A node in the task graph."""
    id: str
    label: str
    status: str
    group: str  # 'task', 'agent', etc.


class GraphEdge(BaseModel):
    """An edge between nodes."""
    from_: str = Field(..., alias="from")
    to: str
    type: str  # 'HAS_PRIORITY', 'DEPENDS_ON', etc.

    class Config:
        populate_by_name = True


class GraphResponse(BaseModel):
    """Complete graph data for visualization."""
    nodes: List[GraphNode]
    edges: List[GraphEdge]


# =============================================================================
# Dependency Injection
# =============================================================================

async def get_graph_db() -> GraphClient:
    """Dependency to get graph client."""
    graph = get_graph()
    if not graph._initialized:
        await graph.initialize()
    return graph


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/tasks", response_model=GraphResponse)
async def get_task_graph(
    graph: GraphClient = Depends(get_graph_db),
):
    """
    Retrieve the task graph from Neo4j.

    Returns nodes (agents and tasks) and edges (relationships).
    Designed for visualization with react-force-graph.
    """
    try:
        # Query 1: Get all task nodes with their status
        task_query = """
        MATCH (t:Task)
        RETURN 
            t.task_id as id,
            t.description as label,
            coalesce(t.status, 'pending') as status,
            'task' as group
        ORDER BY t.created_at DESC
        """
        
        # Query 2: Get all agent nodes
        agent_query = """
        MATCH (a:Agent)
        RETURN 
            a.agent_id as id,
            a.name as label,
            'active' as status,
            'agent' as group
        """
        
        # Query 3: Get HAS_PRIORITY relationships (agent -> task)
        priority_edges_query = """
        MATCH (a:Agent)-[r:HAS_PRIORITY]->(t:Task)
        RETURN 
            a.agent_id as from,
            t.task_id as to,
            'HAS_PRIORITY' as type
        """
        
        # Query 4: Get DEPENDS_ON relationships (task -> task)
        dependency_edges_query = """
        MATCH (t1:Task)-[r:DEPENDS_ON]->(t2:Task)
        RETURN 
            t1.task_id as from,
            t2.task_id as to,
            'DEPENDS_ON' as type
        """
        
        nodes = []
        edges = []
        
        async with graph._driver.session() as session:
            # Fetch tasks
            result = await session.run(task_query)
            records = await result.data()
            for record in records:
                nodes.append(GraphNode(
                    id=record["id"],
                    label=record["label"],
                    status=record["status"],
                    group=record["group"]
                ))
            
            # Fetch agents
            result = await session.run(agent_query)
            records = await result.data()
            for record in records:
                nodes.append(GraphNode(
                    id=record["id"],
                    label=record["label"],
                    status=record["status"],
                    group=record["group"]
                ))
            
            # Fetch priority edges
            result = await session.run(priority_edges_query)
            records = await result.data()
            for record in records:
                edges.append(GraphEdge(
                    **{"from": record["from"], "to": record["to"], "type": record["type"]}
                ))
            
            # Fetch dependency edges
            result = await session.run(dependency_edges_query)
            records = await result.data()
            for record in records:
                edges.append(GraphEdge(
                    **{"from": record["from"], "to": record["to"], "type": record["type"]}
                ))
        
        logger.info(f"Graph fetched: {len(nodes)} nodes, {len(edges)} edges")
        
        return GraphResponse(nodes=nodes, edges=edges)
        
    except Exception as e:
        logger.error(f"Failed to fetch task graph: {e}")
        raise HTTPException(status_code=500, detail=f"Graph query failed: {str(e)}")
