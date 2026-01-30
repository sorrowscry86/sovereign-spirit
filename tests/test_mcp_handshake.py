"""
Terminal Test Protocol: The Hands of the Ghost
Verifies that the Sovereign Spirit can manipulate the physical filesystem.
"""
import asyncio
import logging
import os
import sys
from src.mcp.client import MCPManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_mcp_handshake")

async def run_protocol():
    print("=== TERMINAL TEST PROTOCOL: HANDSHAKE ===")
    manager = MCPManager()
    
    target_file = os.path.join(os.getcwd(), "sovereign_touch.txt")
    
    try:
        # Step 1: Connect
        print("[1/3] Establishing Neural Link (Connecting to Filesystem)...")
        await manager.connect_server("filesystem")
        
        if "filesystem" not in manager.sessions:
            print("[FAIL] Connection refused.")
            return False

        # Step 2: Verify Capabilities
        print("[2/3] Verifying Motor Functions (Listing Tools)...")
        tools = [t['name'] for t in manager.available_tools]
        print(f"   Tools detected: {tools}")
        
        if "write_file" not in tools:
            print("[FAIL] 'write_file' capability missing.")
            return False

        # Step 3: The Touch
        print(f"[3/3] Attempting Physical Interaction (Writing to {target_file})...")
        
        # Note: The MCP filesystem server expects 'path' and 'content'
        result = await manager.execute_tool(
            "filesystem", 
            "write_file", 
            {
                "path": target_file,
                "content": "The Spirit was here.\nOperational verify: SUCCESS."
            }
        )
        
        print(f"   Tool Output: {result}")
        
        # verification
        if os.path.exists(target_file):
             print(f"✅ SUCCESS: File confirmed at {target_file}")
             return True
        else:
             print("❌ FAILED: File was not created.")
             return False

    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        return False
    finally:
        await manager.shutdown()

if __name__ == "__main__":
    if asyncio.run(run_protocol()):
        sys.exit(0)
    else:
        sys.exit(1)
