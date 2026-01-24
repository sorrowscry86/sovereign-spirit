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
from datetime import datetime

from src.core.memory.types import EpisodicMemory, PrismContext, WorkingMemory
from src.core.vector import get_vector_client
from src.core.graph import get_graph
from src.core.cache import get_cache

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
        if self._initialized: return
        
        await asyncio.gather(
            self.vector.initialize(),
            self.graph.initialize(),
            self.cache.initialize()
        )
        self._initialized = True
        logger.info("Memory Prism Initialized (All spectra online)")

    async def recall(self, query: str, agent_id: str, session_id: Optional[str] = None) -> PrismContext:
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
            valence_stripped=True # Explicitly applied in _recall_deep
        )

    async def _recall_fast(self, agent_id: str, session_id: str) -> WorkingMemory:
        """Retrieve working memory (recent history + focus) from Redis."""
        try:
            messages = await self.cache.get_messages(session_id, limit=10)
            focus = await self.cache.get_focus(agent_id)
            
            return WorkingMemory(
                session_id=session_id,
                current_focus=focus or "Awaiting Directive",
                history=[EpisodicMemory(**m) for m in messages]
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
                    tags=r["tags"]
                )
                
                # --- VALENCE STRIPPING LOGIC ---
                # A Sovereign Spirit must shield its heart from others, but never from itself.
                if mem.author_id.lower() == agent_id.lower():
                    # SELF: Keep raw subjective voice and valence
                    memories.append(mem)
                else:
                    # OTHER: Strip valence and subjective color
                    sanitized_mem = mem.model_copy()
                    sanitized_mem.subjective_voice = None # [REDACTED]
                    sanitized_mem.emotional_valence = 0.0 # Neutralized
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
                    "priority": t["priority"]
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
                "tags": memory.tags
            }
            uuid = await self.vector.insert_memory(data)
            if uuid:
                logger.info(f"Stored memory {uuid} for {memory.author_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Memory storage failed: {e}")
            return False

    async def add_chat_message(self, session_id: str, author_id: str, content: str, 
                               voice: Optional[str] = None, valence: float = 0.0):
        """Helper to add a message to the Fast Stream (Working Memory)."""
        if not self._initialized: await self.initialize()
        
        msg = {
            "author_id": author_id,
            "content": content,
            "subjective_voice": voice,
            "emotional_valence": valence,
            "timestamp": datetime.now().isoformat()
        }
        await self.cache.push_message(session_id, msg)


_prism_engine: Optional[PrismEngine] = None

def get_prism() -> PrismEngine:
    global _prism_engine
    if _prism_engine is None:
        _prism_engine = PrismEngine()
    return _prism_engine
