"""
Test Chronos MCP Integration
============================
Verifies that the Chronos MCP server can be started and queried.
"""
import asyncio
import os
import sys

# Ensure project root is in path
sys.path.insert(0, os.path.abspath("."))

from src.mcp.client import MCPManager

async def test_chronos_connection():
    manager = MCPManager()
    
    print(" [1] Connecting to 'chronos' MCP server...")
    try:
        await manager.connect_server("chronos")
        print("  [PASS] Connection established.")
    except Exception as e:
        print(f"  [FAIL] Connection failed: {e}")
        return

    print(" [2] Listing available tools...")
    found_tools = [t for t in manager.available_tools if t["server"] == "chronos"]
    if not found_tools:
        print("  [FAIL] No tools found for chronos server.")
    else:
        print(f"  [PASS] Found {len(found_tools)} tools:")
        for t in found_tools:
            print(f"    - {t['name']}")
            
    await manager.shutdown()

if __name__ == "__main__":
    asyncio.run(test_chronos_connection())
