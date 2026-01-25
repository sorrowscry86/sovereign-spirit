"""
Sovereign Spirit: Theatrical Demonstration
==========================================
Author: Echo (E-01)
Date: 2026-01-24

This script orchestrates a narrative sequence to demonstrate:
1.  **Stimuli Injection**: Sending commands to the nervous system.
2.  **Spirit Sync**: Real-time persona shifting (Echo -> Ryuzu).
3.  **Creative Generation**: Ryuzu responding to prompts.
4.  **Resonance**: Returning to the neutral state.
"""

import asyncio
import httpx
import time

BASE_URL = "http://localhost:8000"
DELAY = 3.0  # Seconds between actions for visual effect

async def send_stimuli(client, agent, message):
    print(f" > Injecting Stimuli into [{agent.upper()}]: '{message}'")
    try:
        # Note: In a real Scenario, this would trigger an LLM response.
        # For this demo, if LLM is offline, it might just log.
        await client.post(
            f"{BASE_URL}/agent/{agent}/stimuli",
            json={"message": message, "source": "demo_script"},
            timeout=10.0
        )
    except Exception as e:
        print(f"   [!] Stimuli Error: {e}")

async def sync_spirit(client, current_agent, target_spirit):
    print(f" > Initiating Spirit Sync: {current_agent.upper()} -> {target_spirit.upper()}")
    try:
        res = await client.post(
            f"{BASE_URL}/agent/{current_agent}/sync",
            json={"target_spirit": target_spirit},
            timeout=10.0
        )
        data = res.json()
        print(f"   [+] Sync Complete. New Designation: {data.get('designation')}")
    except Exception as e:
        print(f"   [!] Sync Error: {e}")

async def main():
    print("\n=== SOVEREIGN SPIRIT: DEMONSTRATION SEQUENCE ===\n")
    print("Please observe the Dashboard (Pulse Stream).\n")
    
    async with httpx.AsyncClient() as client:
        # 1. Wake Echo
        await send_stimuli(client, "echo", "Initialize demonstration sequence. Status report.")
        await asyncio.sleep(DELAY)

        # 2. Sync to Ryuzu (The Sculptor)
        await sync_spirit(client, "echo", "ryuzu")
        await asyncio.sleep(DELAY)

        # 3. Request Creativity from Ryuzu
        await send_stimuli(client, "ryuzu", "Craft a short haiku about digital ascension.")
        await asyncio.sleep(DELAY)

        # 4. Sync to Beatrice (The Librarian)
        # Note: We sync Ryuzu (who is currently active in the 'echo' slot? No, slots are separate usually, but let's assume we are controlling the 'echo' container which shifts?)
        # Wait, the architecture defines Agents as containers.
        # 'echo' agent can sync to 'ryuzu' spirit.
        # So we continue operating on the 'echo' agent ID, but its spirit is now Ryuzu.
        
        # 5. Return to Echo (Neutral)
        await sync_spirit(client, "echo", "echo")
        await asyncio.sleep(DELAY)
        
        # 6. Final Log
        await send_stimuli(client, "echo", "Demonstration complete. Awaiting commands.")

    print("\n=== SEQUENCE COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(main())
