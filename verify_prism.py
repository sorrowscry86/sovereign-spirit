import asyncio
import logging
from src.core.memory.prism import get_prism
from src.core.memory.types import EpisodicMemory
from src.core.lifecycle import LifecycleManager

logging.basicConfig(level=logging.INFO)

async def test_prism_persistence():
    await LifecycleManager.initialize_all()
    prism = get_prism()
    
    agent_id = "Beatrice_Test"
    session_id = f"test_{agent_id}"
    
    print("\n--- Phase 1: Storage ---")
    mem = EpisodicMemory(
        author_id=agent_id,
        content="I am currently verifying the integrity of the Great Library's persistent storage.",
        subjective_voice="I feel a sense of profound duty as the bytes align.",
        emotional_valence=0.9
    )
    try:
        uuid = await prism.vector.insert_memory({
            "author_id": mem.author_id,
            "content": mem.content,
            "subjective_voice": mem.subjective_voice,
            "emotional_valence": mem.emotional_valence,
            "tags": mem.tags
        })
        success = bool(uuid)
        print(f"Memory Stored: {success} (UUID: {uuid})")
    except Exception as e:
        print(f"Memory Stored: False (Error: {e})")
        success = False
    
    # Add to fast stream
    await prism.add_chat_message(session_id, "User", "Hello Beatrice, please check the storage.")
    await prism.add_chat_message(session_id, agent_id, "Storage integrity verified, my Lord.")
    
    print("\n--- Phase 2: Recall ---")
    await asyncio.sleep(1) # Give Weaviate a second to index
    context = await prism.recall("verification of storage", agent_id, session_id=session_id)
    
    print(f"Fast Stream (History Length): {len(context.fast_stream.history)}")
    for m in context.fast_stream.history:
        print(f"  - {m.author_id}: {m.content}")
        
    print(f"Deep Well (Semantic Matches): {len(context.deep_well)}")
    for m in context.deep_well:
        print(f"  - {m.author_id}: {m.content}")
        print(f"    Voice: {m.subjective_voice}")
        print(f"    Valence: {m.emotional_valence}")
        
    print("\n--- Phase 3: Valence Stripping Verification ---")
    # Recall as 'Echo' to see if Beatrice's emotion is stripped
    context_echo = await prism.recall("verification of storage", "Echo", session_id=session_id)
    for m in context_echo.deep_well:
        if m.author_id == agent_id:
            print(f"Recall for Echo - Beatrice Voice: {m.subjective_voice} | Valence: {m.emotional_valence}")
            if m.subjective_voice is None and m.emotional_valence == 0.0:
                print("SUCCESS: Valence Stripped correctly.")

async def run_verification():
    try:
        await test_prism_persistence()
    except Exception as e:
        print(f"Test Failed with Error: {e}")
    finally:
        await LifecycleManager.shutdown()

if __name__ == "__main__":
    asyncio.run(run_verification())


