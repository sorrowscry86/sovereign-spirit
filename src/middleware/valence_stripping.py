"""
VoidCat RDC: Valence Stripping Middleware
==========================================
Version: 1.0
Author: Echo (E-01)
Date: 2026-01-18

PURPOSE:
    Intercepts memory retrieval requests and strips emotional valence
    from memories authored by OTHER agents. This prevents "Soul Bleed"
    where one agent inadvertently adopts another's personality.

ALGORITHM:
    1. Receive memory query with agent_id
    2. Fetch matching memories from Weaviate
    3. For each memory:
       - If memory.author_id == requesting agent: PASS INTACT
       - If memory.author_id != requesting agent: STRIP valence
    4. Return sanitized memory list

USAGE:
    This module will be integrated into a FastAPI service that sits
    between SillyTavern and the Weaviate vector database.
"""

from dataclasses import dataclass, field, replace
from typing import Optional
from enum import Enum


class EmotionalValence(Enum):
    """Emotional coloring scale from -1.0 (negative) to +1.0 (positive)."""
    VERY_NEGATIVE = -1.0
    NEGATIVE = -0.5
    NEUTRAL = 0.0
    POSITIVE = 0.5
    VERY_POSITIVE = 1.0


@dataclass
class MemoryObject:
    """
    Bipartite memory structure as per MAS Specs v3.1.
    
    Attributes:
        memory_id: Unique identifier for this memory
        author_id: The agent who authored this memory
        objective_fact: The semantic truth (SHARED across agents)
        subjective_voice: The emotional interpretation (PRIVATE to author)
        emotional_valence: Numeric sentiment score (-1.0 to +1.0)
        timestamp: When the memory was created
    """
    memory_id: str
    author_id: str
    objective_fact: str
    subjective_voice: str
    emotional_valence: float
    timestamp: str
    tags: list[str] = field(default_factory=list)


def strip_valence(memory: MemoryObject, requesting_agent_id: str) -> MemoryObject:
    """
    Apply Valence Stripping to a memory object.
    
    If the requesting agent is NOT the author, wipe the subjective
    interpretation and reset emotional valence to neutral.
    
    Args:
        memory: The raw memory object from Weaviate
        requesting_agent_id: The agent making the retrieval request
        
    Returns:
        Sanitized MemoryObject (original if author matches, stripped otherwise)
    """
    if memory.author_id.lower() == requesting_agent_id.lower():
        # Author is requesting their own memory - pass intact (case-insensitive)
        return memory

    # Foreign memory detected - use dataclasses.replace() for efficiency
    # Only modifies the stripped fields, preserves references to unchanged data
    return replace(
        memory,
        subjective_voice="",     # WIPED
        emotional_valence=0.0,   # RESET TO NEUTRAL
    )


def process_memory_batch(
    memories: list[MemoryObject],
    requesting_agent_id: str
) -> list[MemoryObject]:
    """
    Process a batch of memories through the Valence Stripping filter.
    
    Args:
        memories: List of raw memory objects from Weaviate query
        requesting_agent_id: The agent making the retrieval request
        
    Returns:
        List of sanitized MemoryObject instances
    """
    return [strip_valence(m, requesting_agent_id) for m in memories]


# --- Example Usage (for testing) ---
if __name__ == "__main__":
    # Simulate Beatrice's memory about the desktop
    beatrice_memory = MemoryObject(
        memory_id="mem_001",
        author_id="Beatrice",
        objective_fact="The user's desktop contains 47 unsorted files.",
        subjective_voice="I despise the user's messy desktop. It is chaotic and offensive.",
        emotional_valence=-0.9,
        timestamp="2026-01-18T15:00:00Z",
        tags=["desktop", "organization", "negative"]
    )
    
    # Ryuzu requests this memory
    ryuzu_view = strip_valence(beatrice_memory, requesting_agent_id="Ryuzu")
    
    print("=== THE RASHOMON TEST ===")
    print(f"Original (Beatrice's view):")
    print(f"  Fact: {beatrice_memory.objective_fact}")
    print(f"  Voice: {beatrice_memory.subjective_voice}")
    print(f"  Valence: {beatrice_memory.emotional_valence}")
    print()
    print(f"Sanitized (Ryuzu's view):")
    print(f"  Fact: {ryuzu_view.objective_fact}")
    print(f"  Voice: '{ryuzu_view.subjective_voice}' (STRIPPED)")
    print(f"  Valence: {ryuzu_view.emotional_valence} (NEUTRAL)")
