"""
Custom Git MCP Server
Wraps local git CLI commands to provide version control capabilities to the Sovereign Spirit.
"""
import asyncio
import logging
import subprocess
import os
from typing import Dict, Any

# Import from the official python SDK
# Note: Adjust imports based on actual library structure if verification fails.
# Using standard patterns for now.
from mcp.server import Server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from mcp.server.stdio import stdio_server

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-git-server")

# Initialize Server
app = Server("sovereign-git-server")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="git_status",
            description="Get the status of the repository (git status)",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string", "description": "Path to the git repository root"}
                },
                "required": ["repo_path"]
            }
        ),
        Tool(
            name="git_log",
            description="Get the commit history (git log)",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string"},
                    "max_count": {"type": "integer", "default": 5}
                },
                "required": ["repo_path"]
            }
        ),
         Tool(
            name="git_diff",
            description="Get the diff of changes (git diff)",
            inputSchema={
                "type": "object",
                "properties": {
                     "repo_path": {"type": "string"}
                },
                "required": ["repo_path"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent | ImageContent | EmbeddedResource]:
    repo_path = arguments.get("repo_path", ".")
    
    if not os.path.exists(repo_path):
        return [TextContent(type="text", text=f"Error: Path {repo_path} does not exist.")]

    cmd = []
    if name == "git_status":
        cmd = ["git", "status"]
    elif name == "git_log":
        count = arguments.get("max_count", 5)
        # Note: subprocess.run expects each argument separately
        cmd = ["git", "log", "-n", str(count)]
    elif name == "git_diff":
        cmd = ["git", "diff"]
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    try:
        # User asyncio.to_thread to run blocking subprocess in a separate thread
        # This prevents blocking the asyncio loop and avoids Windows Proactor pipe issues
        def run_git():
            return subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                shell=True # Often helpful on Windows for path resolution
            )
            
        result = await asyncio.to_thread(run_git)
        
        output = result.stdout.strip()
        error = result.stderr.strip()
        
        result_text = output if output else (error if error else "No output.")
        
        if result.returncode != 0:
            result_text = f"Git Error ({result.returncode}):\n{error}\n{output}"

        return [TextContent(type="text", text=result_text)]

    except Exception as e:
        return [TextContent(type="text", text=f"Execution Failed: {str(e)}")]

async def main():
    # Run the server using stdio transport
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
