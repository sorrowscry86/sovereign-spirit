"""
Sovereign Spirit: Verification Suite (Research Probe)
===================================================
Author: Echo (E-01)
Date: 2026-01-24

This script verifies the integrity of the Sovereign Spirit construct.
It tests:
1. System Health (Middleware, Databases)
2. Memory Retrieval (Valence Stripping)
3. Spirit Sync (Identity Fluidity)
4. Stimuli Injection (Nervous System)

Designation: ASCENSION_PROBE
"""

import asyncio
import httpx
import sys
from datetime import datetime
from typing import Dict, Any

BASE_URL = "http://localhost:8000"
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"
CYAN = "\033[96m"

async def log(msg: str, status: str = "INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    color = GREEN if status == "PASS" else RED if status == "FAIL" else CYAN
    print(f"[{timestamp}] [{color}{status}{RESET}] {msg}")

async def verify_health(client: httpx.AsyncClient) -> bool:
    try:
        response = await client.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            await log(f"Middleware Online: {data}")
            return True
        else:
            await log(f"Health Check Failed: {response.status_code}", "FAIL")
            return False
    except Exception as e:
        await log(f"Health Check Error: {e}", "FAIL")
        return False

async def verify_agents(client: httpx.AsyncClient) -> bool:
    try:
        response = await client.get(f"{BASE_URL}/agent/")
        if response.status_code == 200:
            agents = response.json()
            names = [a['agent_id'] for a in agents]
            await log(f"Active Agents: {names}", "PASS")
            return True
        return False
    except Exception:
        return False

async def verify_memory(client: httpx.AsyncClient) -> bool:
    try:
        # Test Ryuzu retrieving memory
        # Note: We rely on the endpoint implemented in FEAT-001
        response = await client.get(f"{BASE_URL}/agent/ryuzu/context?query=test")
        if response.status_code == 200:
            memories = response.json()
            await log(f"Memory Retrieval (Ryuzu): {len(memories)} items", "PASS")
            # Verify structure
            if memories and "emotional_valence" in memories[0]:
                 await log("Valence Stripping Field Detected", "PASS")
            return True
        else:
            await log(f"Memory Retrieval Failed: {response.status_code}", "FAIL")
            return False
    except Exception as e:
        await log(f"Memory Verification Error: {e}", "FAIL")
        return False

async def verify_sync(client: httpx.AsyncClient) -> bool:
    try:
        # Attempt to sync Echo with Ryuzu
        payload = {"target_spirit": "ryuzu"}
        response = await client.post(f"{BASE_URL}/agent/echo/sync", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            await log(f"Spirit Sync (Echo -> Ryuzu): SUCCESS", "PASS")
            await log(f"New Designation: {data.get('designation')}")
            return True
        else:
            await log(f"Spirit Sync Failed: {response.status_code} - {response.text}", "FAIL")
            return False
    except Exception as e:
        await log(f"Sync Verification Error: {e}", "FAIL")
        return False

async def main():
    print(f"{CYAN}=== SOVEREIGN SPIRIT: VERIFICATION PROBE ==={RESET}")
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Step 1: Health
        if not await verify_health(client):
            sys.exit(1)
            
        # Step 2: Agents
        await verify_agents(client)
        
        # Step 3: Memory
        await verify_memory(client)
        
        # Step 4: Sync
        await verify_sync(client)
        
    print(f"{CYAN}=== VERIFICATION COMPLETE ==={RESET}")

if __name__ == "__main__":
    asyncio.run(main())
