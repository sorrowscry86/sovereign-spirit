"""
VoidCat RDC: Sovereign Spirit Core - Memory Types
=================================================
Data models for the Memory Prism architecture.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field
import uuid

class EpisodicMemory(BaseModel):
    """
    A raw, subjective memory of an event.
    Contains the 'feeling' and 'voice' of the agent.
    """
    memory_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    author_id: str
    content: str
    subjective_voice: Optional[str] = None  # Internal monologue/feeling
    emotional_valence: float = 0.0  # -1.0 to 1.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc)) # Canonical time
    tags: List[str] = []
    
    # Vector embedding placeholder (handled by Weaviate)
    embedding: Optional[List[float]] = None

class SemanticFact(BaseModel):
    """
    An objective fact derived from memories.
    Stripped of emotional coloring. Safe for sharing.
    """
    fact_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    source_memory_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    certainty: float = 1.0

class WorkingMemory(BaseModel):
    """
    Short-term context (Redis).
    """
    session_id: str
    history: List[EpisodicMemory] = [] # Aligned with Prism recall
    current_focus: Optional[str] = None
    active_tools: List[str] = []


class PrismContext(BaseModel):
    """
    The refracted context object returned by the Prism.
    """
    agent_id: str
    query: str
    
    # The Three Beams
    fast_stream: WorkingMemory
    deep_well: List[EpisodicMemory]
    crystalline_web: List[Dict[str, Any]]  # Graph results
    
    # Metadata
    valence_stripped: bool = False  # If true, deep_well contains only facts or sanitized memories
