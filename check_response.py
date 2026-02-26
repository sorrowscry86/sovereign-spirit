
import asyncio
import sys
from sqlalchemy import text

# Add src to path
sys.path.append("/app")

from src.core.database import get_database

async def check():
    print("Connecting to DB...")
    db = get_database()
    await db.initialize()
    
    print("[1] Testing list_agents() again...")
    agents = await db.list_agents()
    target_id = None
    for a in agents:
        print(f"   - Name: '{a.name}' | ID: '{a.agent_id}'")
        if "sonmi" in a.agent_id.lower():
            target_id = a.agent_id

    if not target_id:
        print("[-] No Sonmi agent found in list.")
        return

    print(f"\n[2] Testing get_agent_state('{target_id}')...")
    agent = await db.get_agent_state(target_id)
    if agent:
        print(f"[+] SUCCESS with ID '{target_id}': Found {agent.name}")
    else:
        print(f"[-] FAILED with ID '{target_id}'")
        
        # Try Name
        print(f"[3] Testing get_agent_state('{agents[0].name}')...")
        agent_by_name = await db.get_agent_state(agents[0].name)
        if agent_by_name:
             print(f"[+] SUCCESS with Name '{agents[0].name}'")
        else:
             print("[-] FAILED with Name")

    # [4] Safe DB Access Test
    print("\n[4] Testing Raw SQL Access (No ORM)...")
    async with db.session() as session:
        result = await session.execute(
            text("SELECT action, details, timestamp FROM heartbeat_logs ORDER BY timestamp DESC LIMIT 5")
        )
        rows = result.fetchall()
        for row in rows:
            # Use index access to avoid AttributeError
            timestamp = row[2]
            action = row[0]
            details = row[1]
            print(f"   [{timestamp}] {action}: {str(details)[:30]}...")

if __name__ == "__main__":
    try:
        asyncio.run(check())
    except Exception as e:
        print(f"[-] CRASH: {e}")
