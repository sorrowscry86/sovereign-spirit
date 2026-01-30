
import asyncio
import httpx
import sys

BASE_URL = "http://localhost:8000"

async def test_rashomon():
    print("=== RASHOMON TEST: PERSPECTIVE ISOLATION ===")
    
    # We rely on the hardcoded 'demo_001' memory in main.py for now
    # It has author_id="beatrice"
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        # 1. Beatrice asking (Author) -> Should see Subjective Voice
        print("\n[Case 1] Beatrice (Author) retrieves memory...")
        resp_b = await client.get(f"{BASE_URL}/agent/beatrice/memories?query=test")
        if resp_b.status_code == 200:
            mems = resp_b.json().get("memories", [])
            if mems:
                m = mems[0]
                print(f"   Subjective Voice: '{m.get('subjective_voice', 'N/A')}'")
                if m.get('subjective_voice'):
                    print("   [PASS] Author sees subjective voice.")
                else:
                    print("   [FAIL] Author cannot see subjective voice!")
        else:
            print(f"Failed to query Beatrice: {resp_b.status_code}")

        # 2. Echo asking (Observer) -> Should NOT see Subjective Voice
        print("\n[Case 2] Echo (Observer) retrieves memory...")
        resp_e = await client.get(f"{BASE_URL}/agent/echo/memories?query=test")
        if resp_e.status_code == 200:
            mems = resp_e.json().get("memories", [])
            if mems:
                m = mems[0]
                voice = m.get('subjective_voice')
                print(f"   Subjective Voice: '{voice}'")
                if not voice or voice == "[REDACTED]" or voice == "":
                    print("   [PASS] Observer sees stripped/redacted voice.")
                else:
                    print(f"   [FAIL] LEAK! Observer saw: {voice}")
        else:
            print(f"Failed to query Echo: {resp_e.status_code}")

if __name__ == "__main__":
    asyncio.run(test_rashomon())
