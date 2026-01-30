
import asyncio
from src.core.database import get_database

async def debug_agents():
    db = get_database()
    await db.initialize()
    print("Database Initialized.")
    
    print("Listing agents via list_agents()...")
    agents = await db.list_agents()
    for a in agents:
        print(f" - Found agent: ID='{a.agent_id}', Name='{a.name}'")
        
    print("\nAttempting get_agent_state('ryuzu')...")
    agent = await db.get_agent_state("ryuzu")
    if agent:
        print(f"SUCCESS: Found agent {agent.name}")
    else:
        print("FAILED: Agent 'ryuzu' not found via get_agent_state")

    await db.close()

if __name__ == "__main__":
    asyncio.run(debug_agents())
