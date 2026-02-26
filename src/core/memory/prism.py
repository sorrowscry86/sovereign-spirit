"""
VoidCat RDC: Sovereign Spirit Core - Memory Prism
=================================================
The central retrieval engine that refracts queries through:
1. Fast Stream (Redis)
2. Deep Well (Weaviate)
3. Crystalline Web (Neo4j)

Implements 'Valence Stripping' to prevent Soul Bleed.
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from src.core.memory.types import EpisodicMemory, PrismContext, WorkingMemory
from src.core.vector import get_vector_client
from src.core.graph import get_graph
from src.core.cache import get_cache
from src.core.database import get_database

logger = logging.getLogger("sovereign.prism")


class PrismEngine:
    """
    The Memory Prism.
    """

    def __init__(self):
        self.vector = get_vector_client()
        self.graph = get_graph()
        self.cache = get_cache()
        self._initialized = False

    async def initialize(self):
        """Initialize all memory subsystems."""
        if self._initialized:
            return

        await asyncio.gather(
            self.vector.initialize(), self.graph.initialize(), self.cache.initialize()
        )
        self._initialized = True
        logger.info("Memory Prism Initialized (All spectra online)")

    async def recall(
        self, query: str, agent_id: str, session_id: Optional[str] = None
    ) -> PrismContext:
        """
        Refract the query into a full context object.
        Applies Valence Stripping to Deep Well results.
        """
        if not self._initialized:
            await self.initialize()

        # Default session_id to agent_id if not provided
        sid = session_id or f"session_{agent_id}"

        # Parallel Retrieval
        fast_task = self._recall_fast(agent_id, sid)
        deep_task = self._recall_deep(query, agent_id)
        web_task = self._recall_web(query, agent_id)

        fast, deep, web = await asyncio.gather(fast_task, deep_task, web_task)

        return PrismContext(
            agent_id=agent_id,
            query=query,
            fast_stream=fast,
            deep_well=deep,
            crystalline_web=web,
            valence_stripped=True,  # Explicitly applied in _recall_deep
        )

    async def _recall_fast(self, agent_id: str, session_id: str) -> WorkingMemory:
        """Retrieve working memory (recent history + focus) from Redis."""
        try:
            messages = await self.cache.get_messages(session_id, limit=10)
            focus = await self.cache.get_focus(agent_id)

            return WorkingMemory(
                session_id=session_id,
                current_focus=focus or "Awaiting Directive",
                history=[EpisodicMemory(**m) for m in messages],
            )
        except Exception as e:
            logger.error(f"Fast Recall failed: {e}")
            return WorkingMemory(session_id=session_id, current_focus="Error")

    async def _recall_deep(self, query: str, agent_id: str) -> List[EpisodicMemory]:
        """
        Retrieve episodic memories from Weaviate.
        APPLY VALENCE STRIPPING HERE.
        """
        raw_results = await self.vector.search(query, agent_id, limit=5)

        memories = []
        for r in raw_results:
            try:
                # Map dict to model
                mem = EpisodicMemory(
                    author_id=r["author_id"],
                    content=r["content"],
                    subjective_voice=r["subjective_voice"],
                    emotional_valence=r["emotional_valence"],
                    timestamp=r["timestamp"],
                    tags=r["tags"],
                )

                # --- VALENCE STRIPPING LOGIC ---
                # A Sovereign Spirit must shield its heart from others, but never from itself.
                if mem.author_id.lower() == agent_id.lower():
                    # SELF: Keep raw subjective voice and valence
                    memories.append(mem)
                else:
                    # OTHER: Strip valence and subjective color
                    sanitized_mem = mem.model_copy()
                    sanitized_mem.subjective_voice = None  # [REDACTED]
                    sanitized_mem.emotional_valence = 0.0  # Neutralized
                    memories.append(sanitized_mem)
            except Exception as e:
                logger.warning(f"Failed to process memory result: {e}")

        return memories

    async def _recall_web(self, query: str, agent_id: str) -> List[Dict[str, Any]]:
        """Retrieve graph results from Neo4j."""
        try:
            tasks = await self.graph.get_agent_tasks(agent_id, status="pending")
            return [
                {
                    "type": "Task",
                    "id": t["task_id"],
                    "desc": t["description"],
                    "priority": t["priority"],
                }
                for t in tasks[:5]
            ]
        except Exception as e:
            logger.error(f"Graph query failed: {e}")
            return []

    async def store_memory(self, memory: EpisodicMemory) -> bool:
        """Store a new memory into the Deep Well (Weaviate)."""
        if not self._initialized:
            await self.initialize()

        try:
            # Convert model to Weaviate-compatible dict
            data = {
                "author_id": memory.author_id,
                "content": memory.content,
                "subjective_voice": memory.subjective_voice,
                "emotional_valence": memory.emotional_valence,
                "tags": memory.tags,
            }
            uuid = await self.vector.insert_memory(data)
            if uuid:
                logger.info(f"Stored memory {uuid} for {memory.author_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Memory storage failed: {e}")
            return False

    async def list_memories(
        self,
        agent_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        List episodic memories from the PostgreSQL memory_events table.

        Supports optional filtering by agent name, event_type, and full-text
        search on semantic_fact. Returns a flat list of dicts suitable for
        JSON serialisation.

        Args:
            agent_id: Agent name to filter by (matches agents.name, case-insensitive).
            memory_type: event_type value to filter by (e.g. 'observation', 'action').
            search: Substring to match against semantic_fact (ILIKE).
            limit: Maximum rows to return (clamped to 1-100).

        Returns:
            List of memory dicts with keys: id, agent_id, content, type, timestamp,
            emotional_valence.
        """
        from sqlalchemy import text as sa_text

        db = get_database()
        limit = max(1, min(limit, 100))

        base_query = """
            SELECT
                me.id::text         AS id,
                a.name              AS agent_id,
                me.semantic_fact    AS content,
                me.event_type       AS type,
                me.occurred_at      AS timestamp,
                me.emotional_valence
            FROM memory_events me
            LEFT JOIN agents a ON me.author_id = a.id
            WHERE 1=1
        """
        params: Dict[str, Any] = {"limit": limit}

        if agent_id:
            base_query += " AND LOWER(a.name) = LOWER(:agent_id)"
            params["agent_id"] = agent_id

        if memory_type:
            base_query += " AND me.event_type = :memory_type"
            params["memory_type"] = memory_type

        if search:
            base_query += " AND me.semantic_fact ILIKE :search"
            params["search"] = f"%{search}%"

        base_query += " ORDER BY me.occurred_at DESC LIMIT :limit"

        try:
            async with db.session() as session:
                result = await session.execute(sa_text(base_query), params)
                rows = result.fetchall()
                return [
                    {
                        "id": row.id,
                        "agent_id": row.agent_id or "unknown",
                        "content": row.content,
                        "type": row.type or "observation",
                        "timestamp": (
                            row.timestamp.isoformat() if row.timestamp else None
                        ),
                        "emotional_valence": row.emotional_valence,
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"list_memories query failed: {e}")
            return []

    async def add_chat_message(
        self,
        session_id: str,
        author_id: str,
        content: str,
        voice: Optional[str] = None,
        valence: float = 0.0,
    ):
        """Helper to add a message to the Fast Stream (Working Memory)."""
        if not self._initialized:
            await self.initialize()

        msg = {
            "author_id": author_id,
            "content": content,
            "subjective_voice": voice,
            "emotional_valence": valence,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await self.cache.push_message(session_id, msg)


_prism_engine: Optional[PrismEngine] = None


def get_prism() -> PrismEngine:
    global _prism_engine
    if _prism_engine is None:
        _prism_engine = PrismEngine()
    return _prism_engine
