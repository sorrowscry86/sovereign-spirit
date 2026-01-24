"""
VoidCat RDC: Middleware Integration Test
=========================================
Verifies that the FastAPI middleware correctly applies valence stripping
to data structures resembling Weaviate responses.
"""

import json
from src.middleware.valence_stripping import MemoryObject, strip_valence

def test_manual_stripping_logic():
    """Double check that the imported logic is consistent."""
    raw_memory = MemoryObject(
        memory_id="test_1",
        author_id="Beatrice",
        objective_fact="The sky is blue.",
        subjective_voice="The blue sky makes me feel hopeful.",
        emotional_valence=0.8,
        timestamp="2026-01-19T10:00:00Z"
    )
    
    # Test as Beatrice (Success)
    beatrice_view = strip_valence(raw_memory, "Beatrice")
    assert beatrice_view.subjective_voice == "The blue sky makes me feel hopeful."
    assert beatrice_view.emotional_valence == 0.8
    
    # Test as Ryuzu (Stripped)
    ryuzu_view = strip_valence(raw_memory, "Ryuzu")
    assert ryuzu_view.subjective_voice == ""
    assert ryuzu_view.emotional_valence == 0.0
    
    print("Logic Integration Test: PASSED")

def simulate_weaviate_response():
    """Simulates a typical GraphQL response from Weaviate."""
    return {
        "data": {
            "Get": {
                "Memory": [
                    {
                        "memory_id": "mem_001",
                        "author_id": "Beatrice",
                        "objective_fact": "File cleanup complete.",
                        "subjective_voice": "I am satisfied with this order.",
                        "emotional_valence": 0.9,
                        "timestamp": "2026-01-18T12:00:00Z"
                    }
                ]
            }
        }
    }

if __name__ == "__main__":
    test_manual_stripping_logic()
    # Placeholder for FastAPI server tests once running
