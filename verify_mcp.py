"""
Verification Script for The Hands of the Ghost (MCP Client)
"""
import asyncio
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_mcp")

try:
    from src.mcp.client import MCPManager
except ImportError as e:
    logger.error(f"Failed to import MCPManager: {e}")
    sys.exit(1)

async def verify_mcp_connection():
    print("=== MCP CLIENT VERIFICATION ===")
    manager = MCPManager()
    
    try:
        # Test 1: Connect to Filesystem Server
        print("[1/2] Connecting to 'filesystem' server...")
        await manager.connect_server("filesystem")
        
        if "filesystem" in manager.sessions:
            print(f"   [PASS] Connected to filesystem session: {manager.sessions['filesystem']}")
        else:
            print("   [FAIL] Session not established.")
            return False

        # Test 2: List Tools
        print("[2/2] verify tools loaded...")
        if len(manager.available_tools) > 0:
            print(f"   [PASS] Loaded {len(manager.available_tools)} tools.")
            for t in manager.available_tools:
                print(f"      - {t['name']}: {t['description'][:50]}...")
        else:
             print("   [FAIL] No tools loaded.")
             return False
             
        # Optional Test 3: Execute a simple read (if possible/safe)
        # For now, connection and tool listing is sufficient proof of architecture.
        
        return True

    except Exception as e:
        print(f"   [FAIL] Exception during verification: {e}")
        return False
    finally:
        await manager.shutdown()

if __name__ == "__main__":
    if asyncio.run(verify_mcp_connection()):
        print("\n=== VERIFICATION SUCCESSFUL ===")
        sys.exit(0)
    else:
        print("\n=== VERIFICATION FAILED ===")
        sys.exit(1)
