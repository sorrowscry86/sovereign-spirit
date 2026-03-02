"""
VoidCat RDC: Sovereign Spirit Core - Database Client
=====================================================
Version: 1.0.0
Author: Echo (E-01)
Date: 2026-01-23

Async PostgreSQL client for agent state persistence using SQLAlchemy.
Connects to the voidcat-postgres container in the Sovereign Stack.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy import text
from pydantic import BaseModel, Field

logger = logging.getLogger("sovereign.database")

# =============================================================================
# Configuration
# =============================================================================

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://voidcat:sovereign_spirit@postgres:5432/voidcat_rdc",
)

# Connection pool configuration (tunable via environment)
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
DB_POOL_OVERFLOW = int(os.getenv("DB_POOL_OVERFLOW", "10"))
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "1800"))  # 30 minutes

# =============================================================================
# Pydantic Models
# =============================================================================


class AgentState(BaseModel):
    """Represents the current state of a Sovereign Spirit agent."""

    agent_id: str
    name: str
    designation: str
    current_mood: str
    system_prompt: str
    traits: Dict[str, Any] = Field(default_factory=dict)
    behavior_modes: Dict[str, Any] = Field(default_factory=dict)
    expertise_tags: List[str] = Field(default_factory=list)
    last_active: Optional[datetime] = None
    created_at: Optional[datetime] = None


class StimuliRecord(BaseModel):
    """Represents an incoming stimuli (message) to an agent."""

    agent_id: str
    content: str
    source: str = "external"
    timestamp: Optional[datetime] = None


class QueuedResponse(BaseModel):
    """Represents a queued response from an agent during autonomous operation."""

    agent_id: str
    content: str
    priority: int = 0
    created_at: Optional[datetime] = None


class ProjectRecord(BaseModel):
    """Represents a long-running project assigned to an agent."""

    project_id: str = ""
    title: str
    description: str
    lead_agent_id: Optional[str] = None
    status: str = "active"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    progress_notes: str = ""


# =============================================================================
# Database Client
# =============================================================================


class DatabaseClient:
    """
    Async PostgreSQL client for Sovereign Spirit state persistence.

    Provides methods for:
    - Agent state retrieval and updates
    - Stimuli recording
    - Heartbeat log insertion
    - Queued response management
    """

    def __init__(self, database_url: str = DATABASE_URL):
        self._engine = create_async_engine(
            database_url,
            pool_size=DB_POOL_SIZE,
            max_overflow=DB_POOL_OVERFLOW,
            pool_timeout=DB_POOL_TIMEOUT,
            pool_recycle=DB_POOL_RECYCLE,
            pool_pre_ping=True,
            echo=False,
        )
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        self._initialized = False
        self._url = database_url  # Store original URL for fallback logic

    async def initialize(self) -> None:
        """Initialize connection pool and verify connectivity."""
        try:
            self._engine = create_async_engine(
                self._url,
                pool_size=DB_POOL_SIZE,
                max_overflow=DB_POOL_OVERFLOW,
                pool_timeout=DB_POOL_TIMEOUT,
                pool_recycle=DB_POOL_RECYCLE,
                pool_pre_ping=True,  # Added this back from original
                echo=False,  # Added this back from original
            )

            # Verify connectivity
            async with self._engine.begin() as conn:
                await conn.execute(text("SELECT 1"))

            self._session_factory = async_sessionmaker(
                self._engine, expire_on_commit=False, class_=AsyncSession
            )
            self._initialized = True
            logger.info("Connected to PostgreSQL")

        except Exception as e:
            # Fallback for host-side execution
            error_msg = str(e).lower()
            if (
                "getaddrinfo failed" in error_msg
                or "could not translate host name" in error_msg
            ) and "localhost" not in str(self._engine.url):
                logger.warning(
                    "Database connection failed for Docker host, trying localhost fallback..."
                )
                try:
                    # Construct localhost URL - MUST use render_as_string(hide_password=False)
                    # otherwise SQLAlchemy masks the password as '***'
                    original_url = self._engine.url.render_as_string(
                        hide_password=False
                    )
                    local_url = original_url.replace("@postgres:", "@localhost:")

                    # Create temporary engine to test
                    # from sqlalchemy.ext.asyncio import create_async_engine # REMOVED: Shadows global
                    temp_engine = create_async_engine(local_url)
                    async with temp_engine.begin() as conn:
                        await conn.execute(text("SELECT 1"))

                    # If success, recreate main engine with local URL
                    await self._engine.dispose()
                    self._engine = create_async_engine(
                        local_url,
                        pool_size=5,
                        max_overflow=10,
                        pool_pre_ping=True,
                    )
                    self._session_factory.configure(bind=self._engine)
                    self._initialized = True
                    logger.info("Database connection verified via localhost")
                    return
                except Exception as fallback_e:
                    logger.error(
                        f"Postgres localhost fallback also failed: {fallback_e}"
                    )

            # If not a DNS error or fallback failed, re-raise
            raise e

    async def close(self) -> None:
        """Close the database connection pool."""
        await self._engine.dispose()
        logger.info("Database connection closed")

    @asynccontextmanager
    async def session(self):
        """Provide a transactional scope around operations."""
        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    # =========================================================================
    # Agent State Operations
    # =========================================================================

    async def list_agents(self) -> List[AgentState]:
        """Retrieve all registered agents."""
        async with self.session() as session:
            result = await session.execute(text("""
                    SELECT 
                        name,
                        designation,
                        current_mood,
                        system_prompt_template,
                        traits_json,
                        behavior_modes,
                        expertise_tags,
                        last_active_at,
                        created_at
                    FROM agents
                    ORDER BY name ASC
                """))
            rows = result.fetchall()
            agents = []
            import json

            for row in rows:
                traits = (
                    row[4] if isinstance(row[4], dict) else json.loads(row[4] or "{}")
                )
                modes = (
                    row[5] if isinstance(row[5], dict) else json.loads(row[5] or "{}")
                )
                agents.append(
                    AgentState(
                        agent_id=row[0].lower() if row[0] else "",
                        name=row[0] or "",
                        designation=row[1] or "Unknown",
                        current_mood=row[2] or "Neutral",
                        system_prompt=row[3] or "",
                        traits=traits,
                        behavior_modes=modes,
                        expertise_tags=row[6] if row[6] else [],
                        last_active=row[7],
                        created_at=row[8],
                    )
                )
            return agents

    async def get_agent_state(self, agent_id: str) -> Optional[AgentState]:
        """Retrieve the current state of an agent by name (used as ID)."""
        async with self.session() as session:
            result = await session.execute(
                text("""
                    SELECT id, name, designation, current_mood, 
                           system_prompt_template, traits_json, 
                           behavior_modes, expertise_tags,
                           last_active_at, created_at
                    FROM agents
                    WHERE LOWER(name) = LOWER(:agent_name)
                """),
                {"agent_name": agent_id},
            )
            row = result.fetchone()
            if row:
                import json

                # Handle JSON fields that might be strings or dicts depending on driver
                traits = (
                    row.traits_json
                    if isinstance(row.traits_json, dict)
                    else json.loads(row.traits_json or "{}")
                )
                modes = (
                    row.behavior_modes
                    if isinstance(row.behavior_modes, dict)
                    else json.loads(row.behavior_modes or "{}")
                )

                return AgentState(
                    agent_id=row.name.lower(),
                    name=row.name,
                    designation=row.designation or "",
                    current_mood=row.current_mood or "Neutral",
                    system_prompt=row.system_prompt_template or "",
                    traits=traits,
                    behavior_modes=modes,
                    expertise_tags=row.expertise_tags or [],
                    last_active=row.last_active_at,
                    created_at=row.created_at,
                )
            return None

    async def update_agent_mood(self, agent_id: str, mood: str) -> bool:
        """Update an agent's current mood."""
        async with self.session() as session:
            result = await session.execute(
                text("""
                    UPDATE agents 
                    SET current_mood = :mood, last_active_at = NOW()
                    WHERE LOWER(name) = LOWER(:agent_name)
                """),
                {"agent_name": agent_id, "mood": mood},
            )
            return result.rowcount > 0

    async def update_agent_designation(self, agent_id: str, designation: str) -> bool:
        """Update an agent's current designation (Persona)."""
        async with self.session() as session:
            result = await session.execute(
                text("""
                    UPDATE agents 
                    SET designation = :designation, last_active_at = NOW()
                    WHERE LOWER(name) = LOWER(:agent_name)
                """),
                {"agent_name": agent_id, "designation": designation},
            )
            return result.rowcount > 0

    async def touch_agent(self, agent_id: str) -> bool:
        """Update last_active_at timestamp for an agent."""
        async with self.session() as session:
            result = await session.execute(
                text("""
                    UPDATE agents SET last_active_at = NOW()
                    WHERE LOWER(name) = LOWER(:agent_name)
                """),
                {"agent_name": agent_id},
            )
            return result.rowcount > 0

    # =========================================================================
    # Stimuli Operations
    # =========================================================================

    async def record_stimuli(self, stimuli: StimuliRecord) -> int:
        """Record an incoming stimuli (message) to an agent."""
        async with self.session() as session:
            # First get the agent's UUID
            agent_result = await session.execute(
                text("SELECT id FROM agents WHERE LOWER(name) = LOWER(:agent_name)"),
                {"agent_name": stimuli.agent_id},
            )
            agent_row = agent_result.fetchone()
            if not agent_row:
                return 0

            result = await session.execute(
                text("""
                    INSERT INTO agent_messages 
                        (to_agent_id, content, status, created_at)
                    VALUES 
                        (:agent_uuid, :content, 'received', NOW())
                    RETURNING id
                """),
                {
                    "agent_uuid": agent_row.id,
                    "content": stimuli.content,
                },
            )
            row = result.fetchone()
            return row.id if row else 0

    # =========================================================================
    # Heartbeat Operations
    # =========================================================================

    async def log_heartbeat(
        self, agent_id: str, action: str, details: Optional[str] = None
    ) -> int:
        """Log a heartbeat cycle for an agent."""
        async with self.session() as session:
            # First get the agent's UUID
            agent_result = await session.execute(
                text("SELECT id FROM agents WHERE LOWER(name) = LOWER(:agent_name)"),
                {"agent_name": agent_id},
            )
            agent_row = agent_result.fetchone()
            if not agent_row:
                return 0

            result = await session.execute(
                text("""
                    INSERT INTO heartbeat_logs 
                        (agent_id, action_taken, thought_content, created_at)
                    VALUES 
                        (:agent_uuid, :action, :details, NOW())
                    RETURNING id
                """),
                {
                    "agent_uuid": agent_row.id,
                    "action": action,
                    "details": details,
                },
            )
            row = result.fetchone()
            # Commit is handled by context manager
            return 1 if row else 0

    async def get_recent_heartbeats(
        self, agent_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get recent heartbeat logs for an agent."""
        async with self.session() as session:
            result = await session.execute(
                text("""
                    SELECT h.id, a.name as agent_name, h.action_taken, h.thought_content, h.created_at
                    FROM heartbeat_logs h
                    JOIN agents a ON h.agent_id = a.id
                    WHERE LOWER(a.name) = LOWER(:agent_name)
                    ORDER BY h.created_at DESC
                    LIMIT :limit
                """),
                {"agent_name": agent_id, "limit": limit},
            )
            rows = result.fetchall()
            return [
                {
                    "id": str(row.id),
                    "agent_id": row.agent_name,
                    "action": row.action_taken,
                    "details": row.thought_content,
                    "timestamp": row.created_at,
                }
                for row in rows
            ]

    async def get_system_logs(
        self, limit: int = 10, actions: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Get recent heartbeat logs for the entire system."""
        async with self.session() as session:
            query = """
                SELECT h.id, a.name as agent_name, h.action_taken, h.thought_content, h.created_at
                FROM heartbeat_logs h
                JOIN agents a ON h.agent_id = a.id
            """

            params = {"limit": limit}

            if actions:
                query += " WHERE h.action_taken = ANY(:actions)"
                params["actions"] = actions

            query += " ORDER BY h.created_at DESC LIMIT :limit"

            result = await session.execute(text(query), params)
            rows = result.fetchall()
            return [
                {
                    "id": str(row.id),
                    "agent_id": row.agent_name,
                    "action": row.action_taken,
                    "thought_content": row.thought_content,  # Normalized key for API
                    "trigger": row.action_taken,  # Normalized key for API
                    "timestamp": row.created_at,
                }
                for row in rows
            ]

    # =========================================================================
    # Queued Response Operations
    # =========================================================================

    async def queue_response(self, response: QueuedResponse) -> int:
        """Queue a response for delivery when user reconnects."""
        async with self.session() as session:
            # First get the agent's UUID
            agent_result = await session.execute(
                text("SELECT id FROM agents WHERE LOWER(name) = LOWER(:agent_name)"),
                {"agent_name": response.agent_id},
            )
            agent_row = agent_result.fetchone()
            if not agent_row:
                return 0

            result = await session.execute(
                text("""
                    INSERT INTO agent_messages 
                        (from_agent_id, content, status, priority, created_at)
                    VALUES 
                        (:agent_uuid, :content, 'pending', :priority, NOW())
                    RETURNING id
                """),
                {
                    "agent_uuid": agent_row.id,
                    "content": response.content,
                    "priority": response.priority,
                },
            )
            row = result.fetchone()
            return row.id if row else 0

    async def get_queued_responses(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get all queued responses for an agent (pending, undelivered)."""
        async with self.session() as session:
            result = await session.execute(
                text("""
                    SELECT m.id, m.content, m.priority, m.created_at
                    FROM agent_messages m
                    JOIN agents a ON m.from_agent_id = a.id
                    WHERE LOWER(a.name) = LOWER(:agent_name)
                      AND m.status = 'pending'
                      AND m.delivered_at IS NULL
                    ORDER BY m.priority DESC, m.created_at ASC
                """),
                {"agent_name": agent_id},
            )
            rows = result.fetchall()
            return [
                {
                    "id": row.id,
                    "content": row.content,
                    "priority": row.priority,
                    "created_at": row.created_at,
                }
                for row in rows
            ]

    async def clear_queued_responses(self, agent_id: str) -> int:
        """Mark queued responses as delivered after retrieval."""
        async with self.session() as session:
            result = await session.execute(
                text("""
                    UPDATE agent_messages m
                    SET status = 'delivered', delivered_at = NOW()
                    FROM agents a
                    WHERE m.from_agent_id = a.id
                      AND LOWER(a.name) = LOWER(:agent_name)
                      AND m.status = 'pending'
                      AND m.delivered_at IS NULL
                """),
                {"agent_name": agent_id},
            )
            return result.rowcount

    # =========================================================================
    # Stimuli Retrieval Operations (The Ear)
    # =========================================================================

    async def get_unread_message_count(self, agent_id: str) -> int:
        """Count unread messages (stimuli) waiting for this agent."""
        async with self.session() as session:
            result = await session.execute(
                text("""
                    SELECT COUNT(m.id)
                    FROM agent_messages m
                    JOIN agents a ON m.to_agent_id = a.id
                    WHERE LOWER(a.name) = LOWER(:agent_name)
                      AND m.status = 'received'
                      AND m.delivered_at IS NULL
                """),
                {"agent_name": agent_id},
            )
            return result.scalar() or 0

    async def get_recent_stimuli(
        self, agent_id: str, limit: int = 1
    ) -> List[Dict[str, Any]]:
        """Get most recent unread messages for an agent."""
        async with self.session() as session:
            result = await session.execute(
                text("""
                    SELECT m.id, m.content, m.created_at, 'User' as sender_name
                    FROM agent_messages m
                    JOIN agents a ON m.to_agent_id = a.id
                    WHERE LOWER(a.name) = LOWER(:agent_name)
                      AND m.status = 'received'
                      AND m.delivered_at IS NULL
                    ORDER BY m.created_at DESC
                    LIMIT :limit
                """),
                {"agent_name": agent_id, "limit": limit},
            )
            rows = result.fetchall()
            return [
                {
                    "id": row.id,
                    "content": row.content,
                    "sender": row.sender_name,
                    "timestamp": row.created_at,
                }
                for row in rows
            ]

    async def mark_stimuli_read(self, message_ids: List[int]) -> int:
        """Mark specific stimuli messages as processed."""
        if not message_ids:
            return 0
        async with self.session() as session:
            result = await session.execute(
                text("""
                    UPDATE agent_messages
                    SET status = 'processed', delivered_at = NOW()
                    WHERE id = ANY(:ids)
                """),
                {"ids": message_ids},
            )
            return result.rowcount

    # =========================================================================
    # Project Operations
    # =========================================================================

    async def create_project(
        self,
        title: str,
        description: str,
        lead_agent_id: Optional[str] = None,
    ) -> str:
        """Create a new project and return its project_id."""
        async with self.session() as session:
            result = await session.execute(
                text("""
                    INSERT INTO projects (title, description, lead_agent_id)
                    VALUES (:title, :description, :lead_agent_id)
                    RETURNING project_id
                """),
                {
                    "title": title,
                    "description": description,
                    "lead_agent_id": lead_agent_id,
                },
            )
            await session.commit()
            row = result.mappings().first()
            return row["project_id"] if row else ""

    async def get_project(self, project_id: str) -> Optional[dict]:
        """Get a project by ID."""
        async with self.session() as session:
            result = await session.execute(
                text("SELECT * FROM projects WHERE project_id = :project_id"),
                {"project_id": project_id},
            )
            row = result.mappings().first()
            return dict(row) if row else None

    async def list_projects(self, status: Optional[str] = None) -> List[dict]:
        """List projects, optionally filtered by status."""
        async with self.session() as session:
            if status:
                result = await session.execute(
                    text(
                        "SELECT * FROM projects WHERE status = :status ORDER BY created_at DESC"
                    ),
                    {"status": status},
                )
            else:
                result = await session.execute(
                    text("SELECT * FROM projects ORDER BY created_at DESC")
                )
            return [dict(row) for row in result.mappings().all()]

    async def update_project_status(self, project_id: str, status: str) -> bool:
        """Update project status."""
        async with self.session() as session:
            result = await session.execute(
                text("""
                    UPDATE projects
                    SET status = :status, updated_at = NOW()
                    WHERE project_id = :project_id
                """),
                {"project_id": project_id, "status": status},
            )
            await session.commit()
            return result.rowcount > 0

    async def append_project_progress(self, project_id: str, note: str) -> None:
        """Append a timestamped line to the project's progress notes."""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        line = f"[{timestamp}] {note}\n"
        async with self.session() as session:
            await session.execute(
                text("""
                    UPDATE projects
                    SET progress_notes = progress_notes || :line,
                        updated_at = NOW()
                    WHERE project_id = :project_id
                """),
                {"project_id": project_id, "line": line},
            )
            await session.commit()

    async def get_active_project_for_agent(self, agent_id: str) -> Optional[dict]:
        """Get the most recent active project assigned to an agent."""
        async with self.session() as session:
            result = await session.execute(
                text("""
                    SELECT * FROM projects
                    WHERE lead_agent_id = :agent_id AND status = 'active'
                    ORDER BY updated_at DESC
                    LIMIT 1
                """),
                {"agent_id": agent_id},
            )
            row = result.mappings().first()
            return dict(row) if row else None


# =============================================================================
# Singleton Instance
# =============================================================================

_db_client: Optional[DatabaseClient] = None


def get_database() -> DatabaseClient:
    """Get or create the singleton database client."""
    global _db_client
    if _db_client is None:
        _db_client = DatabaseClient()
    return _db_client
