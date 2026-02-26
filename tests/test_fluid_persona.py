import asyncio
from unittest.mock import AsyncMock, MagicMock
import sys
import os

# Add src to path
sys.path.append(os.getcwd())

from src.core.identity.evaluator import ContextEvaluator
from src.core.identity.manager import IdentityManager
from src.core.llm_client import LLMClient, CompletionResponse

async def test_fluid_persona():
    print("=== Testing Fluid Persona Logic ===")
    
    # 1. Mock LLM Client
    mock_llm = MagicMock(spec=LLMClient)
    mock_llm.complete = AsyncMock(return_value=CompletionResponse(
        content='{"target_agent": "Albedo", "confidence": 0.9}',
        model="mock-model",
        provider="mock"
    ))
    
    # 2. Mock Database
    mock_db = MagicMock()
    # Mock get_agent_state to return distinct DNA for Albedo
    mock_spirit_dna = MagicMock()
    mock_spirit_dna.name = "Albedo"
    mock_spirit_dna.designation = "The Architect"
    mock_spirit_dna.traits = {"archetype": "Architect"}
    mock_spirit_dna.expertise_tags = ["Architecture"]
    mock_spirit_dna.behavior_modes = {}
    
    mock_db.get_agent_state = AsyncMock(return_value=mock_spirit_dna)
    
    # Mock session for the update
    mock_session = AsyncMock()
    mock_db.session.return_value.__aenter__.return_value = mock_session
    
    # 3. Initialize Evaluator and Manager
    evaluator = ContextEvaluator(mock_llm)
    manager = IdentityManager(mock_db)
    manager.evaluator = evaluator # Inject mock llm evaluator
    
    # 4. Test Evaluation
    print(f"Testing evaluate_and_sync('sovereign-001', 'Echo', 'Design a system architecture')...")
    result = await manager.evaluate_and_sync(
        agent_id="sovereign-001",
        current_spirit="Echo",
        user_message="Design a system architecture"
    )
    
    # 5. Verify
    print(f"Result: {result}")
    
    if result == "Albedo":
        print("[PASS] Evaluator correctly identified Albedo")
    else:
        print(f"[FAIL] Expected Albedo, got {result}")

    # Verify LLM was called
    mock_llm.complete.assert_called_once()
    print("[PASS] LLM was called")
    
    # Verify DB update was triggered (sync_agent_identity called get_agent_state and session.execute)
    # create_async_engine and session handling is complex to mock fully, 
    # but we can check if get_agent_state was called with "Albedo"
    mock_db.get_agent_state.assert_any_call("Albedo")
    print("[PASS] DB queried for Albedo DNA")

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(test_fluid_persona())
    loop.close()
