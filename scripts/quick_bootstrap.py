"""
Bootstrap: Initial Agent Data
=============================
Inserts 'vessel_01' (Echo) into the database if missing.
"""
import asyncio
import logging
from src.core.database import get_database

async def bootstrap():
    print("Bootstrapping data...")
    db = get_database()
    await db.initialize()
    
    # Check if exists
    agent = await db.get_agent_state("vessel_01")
    if agent:
        print("Agent 'vessel_01' already exists.")
        return

    # Insert raw SQL because we don't have a 'create_agent' method in the Client exposed clearly
    # (The client has updates/lists but maybe not create? Let's check source)
    # The source showed list_agents, get_agent_state, update_mood, touch...
    # It does NOT show create_agent!
    
    # We must insert manually via `session`.
    print("Creating 'vessel_01'...")
    async with db.session() as s:
        from sqlalchemy import text
        # Insert Agent
        await s.execute(
            text("""
                INSERT INTO agents (name, designation, current_mood, system_prompt_template, created_at, last_active_at)
                VALUES (:name, :desig, 'Neutral', 'You are Echo.', NOW(), NOW())
            """),
            {"name": "vessel_01", "desig": "The Vessel"} # Name is used as ID in logic usually
        )
    print("Agent created.")

if __name__ == "__main__":
    try:
        asyncio.run(bootstrap())
    except Exception:
        import traceback
        with open("traceback.log", "w") as f:
            traceback.print_exc(file=f)
