"""
Sovereign Spirit: SillyTavern Sync Test
=======================================
Verifies the new Phase D endpoints.
"""

import asyncio
import httpx
import sys

BASE_URL = "http://localhost:8000"

async def test_st_sync():
    print("=== SILLYTAVERN SYNC TEST ===")
    async with httpx.AsyncClient(timeout=10.0) as client:
        # 1. Test Export (Ryuzu)
        print("Testing Export: /st/character/ryuzu...")
        resp = await client.get(f"{BASE_URL}/st/character/ryuzu")
        if resp.status_code == 200:
            card = resp.json()
            print(f"SUCCESS: Exported card for {card.get('name')}")
            print(f"Description: {card.get('description')[:50]}...")
        else:
            print(f"FAILED: Export returned {resp.status_code}")
            return

        # 2. Test Import
        print("\nTesting Import...")
        test_card = {
            "name": "TestSpirit",
            "description": "A spirit born from verification.",
            "personality": "Logical, precise.",
            "creator_notes": "Sovereign Test",
            "system_prompt": "You are a test spirit.",
            "tags": ["test", "verification"]
        }
        resp = await client.post(f"{BASE_URL}/st/character/import", json=test_card)
        if resp.status_code == 200:
            print(f"SUCCESS: Imported {resp.json().get('agent_name')}")
        else:
            print(f"FAILED: Import returned {resp.status_code}")

if __name__ == "__main__":
    try:
        asyncio.run(test_st_sync())
    except Exception as e:
        print(f"ERROR: {e}")
