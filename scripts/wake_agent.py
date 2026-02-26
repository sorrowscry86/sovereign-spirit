
import asyncio
import aiohttp
import sys

# Configuration
API_URL = "http://localhost:8000"
AGENT_ID = "sonmi-451"  # Target Agent (The Archivist)
MESSAGE = "Analyze the metaphysical implications of 'Soul Bleed' within our memory architecture. Be precise."

async def wake_the_sleeper():
    print(f"[*] Attempting to wake {AGENT_ID}...")
    
    async with aiohttp.ClientSession() as session:
        # 1. Send Message to /stimuli endpoint
        # Schema from src/api/agents.py: StimuliRequest(message: str, source: str, metadata: dict)
        payload = {
            "message": MESSAGE,
            "source": "user",
            "metadata": {"type": "verification"}
        }
        
        url = f"{API_URL}/agent/{AGENT_ID}/stimuli"
        
        print(f"[*] Sending stimulus to: {url}")
        print(f"[*] Payload: {payload}")
        
        try:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"[+] Message Delivered. Status: {response.status}")
                    print(f"[+] Response: {data}")
                else:
                    print(f"[-] Failed to send message. Status: {response.status}")
                    text = await response.text()
                    print(f"[-] Details: {text}")
        except Exception as e:
            print(f"[!] connection error: {e}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(wake_the_sleeper())
