
import asyncio
import httpx
import sys

BASE_URL = "http://localhost:8000"

async def test_heartbeat():
    print("=== SOVEREIGN SPIRIT: HEARTBEAT TEST ===")
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Case 1: Trigger Heartbeat (Expect SLEEP if no tasks)
        print("\n[Case 1] Triggering Heartbeat for Ryuzu...")
        resp = await client.post(f"{BASE_URL}/agent/ryuzu/cycle", json={"force": True})
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"   Status: {resp.status_code}")
            print(f"   Action: {data.get('action')}")
            print(f"   Details: {data.get('details')}")
            print(f"   Cycle ID: {data.get('cycle_id')}")
            
            if data.get("cycle_id"):
                print("   [PASS] Heartbeat successfully logged.")
            else:
                print("   [FAIL] No Cycle ID returned.")
        else:
             print(f"   [FAIL] Heartbeat request failed: {resp.status_code}")
             print(f"   Error: {resp.text}")

if __name__ == "__main__":
    asyncio.run(test_heartbeat())
