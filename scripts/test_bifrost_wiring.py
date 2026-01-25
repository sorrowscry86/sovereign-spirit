
import asyncio
import logging
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.llm_client import get_llm_client, ChatMessage

# Mock logging to see warnings
logging.basicConfig(level=logging.INFO)

async def test_wiring():
    client = get_llm_client()
    messages = [ChatMessage(role="user", content="Hello")]

    print("\n--- TEST 1: LOCAL ONLY (Expected: Success or Local Failure, NO Cloud Attempt) ---")
    client.inference_mode = "LOCAL"
    try:
        # This will likely fail in this env since Ollama isn't running, 
        # but we want to see it NOT try Cloud.
        resp = await client.complete(messages)
        print(f"Result: {resp.provider} (UNEXPECTED SUCCESS)")
    except Exception as e:
        print(f"Expected Error (Local Only): {e}")

    print("\n--- TEST 2: CLOUD ONLY (Expected: Runtime Error if no key, NO Local Attempt) ---")
    client.inference_mode = "CLOUD"
    try:
        # Since we haven't provided a real API key in .env, this should fail at the Cloud attempt
        # OR if no cloud providers are in the list, it should raise the "No providers available" error.
        resp = await client.complete(messages)
        print(f"Result: {resp.provider} (UNEXPECTED SUCCESS)")
    except Exception as e:
        print(f"Expected Error (Cloud Only): {e}")

    print("\n--- TEST 3: AUTO (Expected: Failover order) ---")
    client.inference_mode = "AUTO"
    try:
        resp = await client.complete(messages)
        print(f"Result: {resp.provider}")
    except Exception as e:
        print(f"Expected Error (AUTO - All failed): {e}")

if __name__ == "__main__":
    asyncio.run(test_wiring())
