
import asyncio
import json
import os
import sys

# Mock for testing
class MockAgent:
    def __init__(self):
        self.id = "test-uuid"
        self.name = "Beatrice"
        self.designation = "Guardian"
        self.archetype = "Guardian"
        # Test with a dict (like Alchemy returns)
        self.traits_json = {"big_five": {"openness": 90}}
        self.behavior_modes = {}

async def test_trait_parsing():
    agent = MockAgent()
    raw_traits = agent.traits_json
    print(f"DEBUG: raw_traits type: {type(raw_traits)}")
    
    if isinstance(raw_traits, str):
        traits = json.loads(raw_traits)
    elif isinstance(raw_traits, (dict, list)):
        traits = raw_traits
    else:
        traits = {}
        
    print(f"DEBUG: traits parsed: {traits}")
    print("SUCCESS: Mock parsing works.")

if __name__ == "__main__":
    asyncio.run(test_trait_parsing())
