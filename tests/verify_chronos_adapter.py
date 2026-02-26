"""
Verify Chronos Adapter
======================
Integration test for the ChronosAdapter.
"""
import asyncio
import os
import sys

# Ensure project root is in path
sys.path.insert(0, os.path.abspath("."))

from src.mcp.client import MCPManager
from src.adapters.chronos_adapter import ChronosAdapter

async def verify_adapter():
    manager = MCPManager()
    adapter = ChronosAdapter(manager)
    
    print("=== VERIFYING CHRONOS ADAPTER ===")
    
    # 1. List Tasks (Should be empty or have existing)
    print("\n[1] Listing Tasks...")
    tasks = await adapter.list_tasks()
    print(f"    Result: {tasks}")
    
    # 2. Schedule a Test Task
    task_name = "SovereignAdapterTest"
    print(f"\n[2] Scheduling Task '{task_name}' (Wake in 3600s)...")
    # We use a dummy command
    res = await adapter.schedule_task(
        name=task_name,
        command="powershell.exe",
        arguments="-Command \"Write-Host 'Hello from Chronos'\"",
        wake_seconds=3600
    )
    print(f"    Result: {res}")
    
    # 3. Verify it exists
    print("\n[3] Verifying existence...")
    tasks_after = await adapter.list_tasks()
    if task_name in tasks_after:
         print("    [PASS] Task found in list.")
    else:
         print(f"    [FAIL] Task '{task_name}' NOT found in list. Raw list:\n{tasks_after}")
         
    # 4. Clean up
    print(f"\n[4] Deleting Task '{task_name}'...")
    del_res = await adapter.delete_task(task_name)
    print(f"    Result: {del_res}")
    
    # 5. Verify deletion
    tasks_final = await adapter.list_tasks()
    if task_name not in tasks_final:
        print("    [PASS] Task successfully removed.")
    else:
        print("    [FAIL] Task still exists.")

    await manager.shutdown()

if __name__ == "__main__":
    asyncio.run(verify_adapter())
