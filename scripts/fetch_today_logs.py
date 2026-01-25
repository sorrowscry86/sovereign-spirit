
import asyncio
import sys
import os
from datetime import datetime, date

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.database import get_database

async def fetch_today_logs():
    db = get_database()
    await db.initialize()
    
    async with db.session() as session:
        from sqlalchemy import text
        today = date.today().isoformat()
        print(f"Fetching logs for: {today}")
        
        result = await session.execute(
            text("""
                SELECT h.created_at, a.name, h.action_taken, h.thought_content
                FROM heartbeat_logs h
                JOIN agents a ON h.agent_id = a.id
                WHERE h.created_at::date = CURRENT_DATE
                ORDER BY h.created_at ASC
            """)
        )
        rows = result.fetchall()
        
        print(f"Total Heartbeat Logs Found: {len(rows)}")
        for row in rows:
            print(f"[{row[0]}] {row[1]} -> {row[2]}")
            if row[3]:
                print(f"Thought: {row[3]}")
            print("-" * 40)

if __name__ == "__main__":
    asyncio.run(fetch_today_logs())
