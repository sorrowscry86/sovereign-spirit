"""
MCP Server Registry
Defines the local tools available to the Sovereign Spirit Core.
"""
import os
import shutil
from typing import Dict, Any

# Locate npx on the host system dynamically.
# This ensures compatibility across Windows (.cmd) and Linux.
NPX_PATH = shutil.which("npx") or shutil.which("npx.cmd") or "npx"

MCP_SERVER_REGISTRY = {
    "filesystem": {
        "command": NPX_PATH,
        # SECURITY WARNING: We grant access to the current project directory (os.getcwd()).
        # The Spirit can read/write files here.
        "args": ["-y", "@modelcontextprotocol/server-filesystem", os.getcwd()],
        "env": {"PATH": os.environ["PATH"]} 
    },
    "git": {
        "command": "python",
        "args": ["-m", "src.mcp.servers.git"],
        "env": {"PATH": os.environ["PATH"], "PYTHONUNBUFFERED": "1"}
    }
}

def get_server_config(server_name: str) -> Dict[str, Any] | None:
    return MCP_SERVER_REGISTRY.get(server_name)
