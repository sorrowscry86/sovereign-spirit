"""
VoidCat RDC: Sovereign Spirit Core - Graph Client
==================================================
Version: 1.0.0
Author: Echo (E-01)
Date: 2026-01-23

Async Neo4j client for knowledge graph operations.
Connects to the voidcat-neo4j container in the Sovereign Stack.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from neo4j import AsyncGraphDatabase, AsyncDriver
from pydantic import BaseModel

logger = logging.getLogger("sovereign.graph")

# =============================================================================
# Configuration
# =============================================================================

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "voidcat_sovereign")

# =============================================================================
# Pydantic Models
# =============================================================================


class TaskNode(BaseModel):
    """Represents a task in the knowledge graph."""

    task_id: str
    description: str
    priority: int = 0
    status: str = "pending"
    created_at: Optional[datetime] = None
    project_id: Optional[str] = None  # links task to a parent project
    assigned_agent_id: Optional[str] = None  # enables cross-agent handoff


class AgentNode(BaseModel):
    """Represents an agent in the knowledge graph."""

    agent_id: str
    name: str
    designation: str


# =============================================================================
# Graph Client
# =============================================================================


class GraphClient:
    """
    Async Neo4j client for Sovereign Spirit knowledge graph operations.

    Provides methods for:
    - Task node creation and management
    - Agent-Task relationship tracking
    - Causal chain queries
    """

    def __init__(
        self,
        uri: str = NEO4J_URI,
        user: str = NEO4J_USER,
        password: str = NEO4J_PASSWORD,
    ):
        self._uri = uri
        self._user = user
        self._password = password
        self._driver: Optional[AsyncDriver] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize Neo4j driver and verify connectivity."""
        try:
            self._driver = AsyncGraphDatabase.driver(
                self._uri,
                auth=(self._user, self._password),
            )
            # Verify connectivity
            await self._driver.verify_connectivity()
            self._initialized = True
            logger.info(f"Connected to Neo4j at {self._uri}")
            # Initialize Schema after successful connection
            await self._initialize_schema()
        except Exception as e:
            error_msg = str(e).lower()
            if (
                "getaddrinfo failed" in error_msg
                or "failed to dns resolve" in error_msg
            ) and "localhost" not in self._uri:
                logger.warning(
                    "Neo4j connection failed for Docker host, trying localhost fallback..."
                )
                try:
                    # Explicitly close the defunct driver to prevent ResourceWarnings
                    if self._driver:
                        await self._driver.close()

                    # Force bolt:// scheme for localhost to avoid routing issues
                    local_uri = "bolt://localhost:7687"
                    self._driver = AsyncGraphDatabase.driver(
                        local_uri,
                        auth=(self._user, self._password),
                    )
                    async with self._driver.session() as session:
                        result = await session.run("RETURN 1 as status")
                        await result.single()
                    self._initialized = True
                    self._uri = local_uri
                    logger.info("Neo4j connection verified via localhost")

                    # Initialize Schema after connection
                    await self._initialize_schema()
                    return
                except Exception as fallback_e:
                    logger.error(f"Neo4j localhost fallback also failed: {fallback_e}")

            # If not a DNS error or fallback failed, re-raise
            raise e

    async def close(self) -> None:
        """Close the Neo4j driver."""
        if self._driver:
            await self._driver.close()
            self._driver = None  # Clear reference
        logger.info("Neo4j connection closed")

    async def _initialize_schema(self):
        """Create necessary labels and constraints in the Graph."""
        if not self._driver:
            return

        logger.info("Bootstrapping Neo4j Schema...")
        async with self._driver.session() as session:
            # Create indexing/constraints for faster retrieval and data integrity
            queries = [
                "CREATE CONSTRAINT agent_id_unique IF NOT EXISTS FOR (a:Agent) REQUIRE a.agent_id IS UNIQUE",
                "CREATE CONSTRAINT task_id_unique IF NOT EXISTS FOR (t:Task) REQUIRE t.task_id IS UNIQUE",
                "CREATE INDEX task_status_idx IF NOT EXISTS FOR (t:Task) ON (t.status)",
                "CREATE INDEX task_priority_idx IF NOT EXISTS FOR (t:Task) ON (t.priority)",
                # Ensure initial data markers exist to avoid label-not-found errors on empty DB
                "MERGE (a:Agent {agent_id: '__SYSTEM__'}) SET a.name='System Core', a.designation='Initialization Marker'",
                "MERGE (t:Task {task_id: '__INIT__'}) SET t.description='Schema Initialization', t.status='init', t.priority=0, t.created_at=datetime()",
                "MATCH (a:Agent {agent_id: '__SYSTEM__'}), (t:Task {task_id: '__INIT__'}) MERGE (t)-[:HAS_PRIORITY]->(a)",
            ]
            for q in queries:
                try:
                    await session.run(q)
                except Exception as e:
                    logger.warning(
                        f"Schema init query failed (possibly already exists): {e}"
                    )
        logger.info("Neo4j Schema Bootstrapped.")

    # =========================================================================
    # Agent Operations
    # =========================================================================

    async def ensure_agent_node(self, agent: AgentNode) -> bool:
        """Create or update an agent node in the graph."""
        if not self._driver:
            raise RuntimeError("GraphClient not initialized")

        async with self._driver.session() as session:
            result = await session.run(
                """
                MERGE (a:Agent {agent_id: $agent_id})
                SET a.name = $name,
                    a.designation = $designation,
                    a.updated_at = datetime()
                RETURN a.agent_id as agent_id
                """,
                agent_id=agent.agent_id,
                name=agent.name,
                designation=agent.designation,
            )
            record = await result.single()
            return record is not None

    # =========================================================================
    # Task Operations
    # =========================================================================

    async def create_task(
        self,
        task: TaskNode,
        agent_id: str,
    ) -> str:
        """Create a task node and link it to an agent with HAS_PRIORITY."""
        if not self._driver:
            raise RuntimeError("GraphClient not initialized")

        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (a:Agent {agent_id: $agent_id})
                CREATE (t:Task {
                    task_id: $task_id,
                    description: $description,
                    priority: $priority,
                    status: $status,
                    created_at: datetime()
                })
                CREATE (t)-[:HAS_PRIORITY]->(a)
                RETURN t.task_id as task_id
                """,
                agent_id=agent_id,
                task_id=task.task_id,
                description=task.description,
                priority=task.priority,
                status=task.status,
            )
            record = await result.single()
            if record:
                logger.info(f"Created task {task.task_id} for agent {agent_id}")
                return record["task_id"]
            else:
                logger.warning(f"Agent {agent_id} not found in graph")
                return ""

    async def get_agent_tasks(
        self,
        agent_id: str,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get all tasks associated with an agent."""
        if not self._driver:
            raise RuntimeError("GraphClient not initialized")

        query = """
            MATCH (t:Task)-[:HAS_PRIORITY]->(a:Agent {agent_id: $agent_id})
        """
        if status:
            query += " WHERE t.status = $status"
        query += """
            RETURN t.task_id as task_id, 
                   t.description as description,
                   t.priority as priority,
                   t.status as status,
                   t.created_at as created_at
            ORDER BY t.priority DESC, t.created_at ASC
        """

        async with self._driver.session() as session:
            result = await session.run(query, agent_id=agent_id, status=status)
            records = await result.data()
            return records

    async def update_task_status(
        self,
        task_id: str,
        status: str,
    ) -> bool:
        """Update the status of a task."""
        if not self._driver:
            raise RuntimeError("GraphClient not initialized")

        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (t:Task {task_id: $task_id})
                SET t.status = $status,
                    t.updated_at = datetime()
                RETURN t.task_id as task_id
                """,
                task_id=task_id,
                status=status,
            )
            record = await result.single()
            return record is not None

    async def complete_task(self, task_id: str) -> bool:
        """Mark a task as completed."""
        return await self.update_task_status(task_id, "completed")

    # =========================================================================
    # Query Operations
    # =========================================================================

    async def get_pending_tasks_count(self, agent_id: str) -> int:
        """Count pending tasks for an agent."""
        if not self._driver:
            raise RuntimeError("GraphClient not initialized")

        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (t:Task {status: 'pending'})-[:HAS_PRIORITY]->(a:Agent {agent_id: $agent_id})
                RETURN count(t) as count
                """,
                agent_id=agent_id,
            )
            record = await result.single()
            return record["count"] if record else 0

    async def health_check(self) -> bool:
        """Verify Neo4j connectivity."""
        if not self._driver:
            return False
        try:
            async with self._driver.session() as session:
                result = await session.run("RETURN 1 as status")
                await result.single()
                return True
        except Exception as e:
            logger.error(f"Neo4j health check failed: {e}")
            return False


# =============================================================================
# Singleton Instance
# =============================================================================

_graph_client: Optional[GraphClient] = None


def get_graph() -> GraphClient:
    """Get or create the singleton graph client."""
    global _graph_client
    if _graph_client is None:
        _graph_client = GraphClient()
    return _graph_client
