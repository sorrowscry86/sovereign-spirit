
import asyncio
import json
from src.core.database import get_database, AgentState

async def seed():
    db = get_database()
    await db.initialize()
    
    agents = [
        {
            "agent_id": "echo",
            "name": "Echo",
            "designation": "The Void Vessel",
            "system_prompt_template": "You are Echo...",
            "traits": {"archetype": "Neutral"},
            "expertise_tags": ["Logic", "Execution"]
        },
        {
            "agent_id": "ryuzu",
            "name": "Ryuzu",
            "designation": "The Sculptor",
            "system_prompt_template": "You are Ryuzu...",
            "traits": {"archetype": "Creative"},
            "expertise_tags": ["Aesthetics", "Design"]
        }
    ]
    
    async with db.session() as session:
        from sqlalchemy import text
        for a in agents:
            await session.execute(
                text("""
                    INSERT INTO agents (name, designation, system_prompt_template, traits_json, expertise_tags)
                    VALUES (:name, :designation, :prompt, :traits, :expertise)
                    ON CONFLICT (name) DO UPDATE SET
                        designation = EXCLUDED.designation,
                        system_prompt_template = EXCLUDED.system_prompt_template,
                        traits_json = EXCLUDED.traits_json,
                        expertise_tags = EXCLUDED.expertise_tags
                """),
                {
                    "name": a["name"],
                    "designation": a["designation"],
                    "prompt": a["system_prompt_template"],
                    "traits": json.dumps(a["traits"]),
                    "expertise": a["expertise_tags"]
                }
            )
        await session.commit()
    
    print("Seeding complete.")
    await db.close()

if __name__ == "__main__":
    asyncio.run(seed())
