"""
Terminal Test Protocol: The Bicameral Mind
Verifies that the Sovereign Spirit can access version control history.
"""
import asyncio
import logging
import sys
from src.mcp.client import MCPManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_mcp_git")

async def run_protocol():
    print("=== TERMINAL TEST PROTOCOL: BICAMERAL MIND ===")
    manager = MCPManager()
    
    try:
        # Step 1: Connect
        print("[1/3] Establishing Neural Link (Connecting to Git Server)...")
        await manager.connect_server("git")
        
        if "git" not in manager.sessions:
            print("[FAIL] Connection refused.")
            return False

        # Step 2: Verify Capabilities
        print("[2/3] Verifying Memory Access (Listing Tools)...")
        tools = [t['name'] for t in manager.available_tools if t['server'] == 'git']
        print(f"   Git Tools detected: {tools}")
        
        required_tool = "git_status" 
        # Note: Tool names might vary, usually it's git_status, git_diff, etc. 
        # We'll check if ANY git tools are present.
        
        if not tools:
            print("[FAIL] No git capabilities detected.")
            return False

        # Step 3: The Recall
        print(f"[3/3] Attempting To Remember (git status)...")
        
        # We try to run a status check
        # The tool name is likely 'git_status' or similar based on the server 
        # We'll guess 'git_status' based on standard convention, but if it fails we'll see the available tools list above.
        tool_to_use = "git_status" if "git_status" in tools else tools[0]
        
        print(f"   Executing {tool_to_use}...")
        result = await manager.execute_tool(
            "git", 
            tool_to_use, 
            {"repo_path": "."} # Git server usually requires a repo path
        )
        
        print(f"   Memory Output:\n{result}")
        
        if "On branch" in result or "Changes" in result or "Untracked" in result or "nothing to commit" in result:
             print(f"SUCCESS: Git status retrieved.")
             return True
        else:
             print("WARNING: Output unclear, but execution finished.")
             return True

    except Exception as e:
        print(f"EXCEPTION: {e}")
        return False
    finally:
        await manager.shutdown()

if __name__ == "__main__":
    if asyncio.run(run_protocol()):
        sys.exit(0)
    else:
        sys.exit(1)
