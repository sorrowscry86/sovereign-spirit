"""
Chronos MCP Server
==================
The Timekeeper of the Sovereign Spirit.
Wraps Windows Task Scheduler to allow the Spirit to schedule its own execution.
"""

import asyncio
import logging
import subprocess
import sys
import os
import json
from typing import Dict, Any, List, Optional

from mcp.server import Server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from mcp.server.stdio import stdio_server

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-chronos-server")

# Constants
WRAPPER_SCRIPT = os.path.join("scripts", "mcp", "chronos", "chronos_wrappers.ps1")
POWERSHELL_CMD = "powershell"

app = Server("sovereign-chronos-server")

async def run_powershell(command: str) -> str:
    """Helper to run PowerShell commands loading the wrapper functions first."""
    
    # We dot-source the wrapper script, then run the command.
    # We use -ExecutionPolicy Bypass to ensure it runs.
    full_command = f". .\\{WRAPPER_SCRIPT}; {command}"
    
    # Check if script exists first
    if not os.path.exists(WRAPPER_SCRIPT):
        return f"Error: Wrapper script not found at {os.path.abspath(WRAPPER_SCRIPT)}"

    def _exec():
        return subprocess.run(
            [POWERSHELL_CMD, "-ExecutionPolicy", "Bypass", "-Command", full_command],
            capture_output=True,
            text=True,
            cwd=os.getcwd() # Run from project root
        )

    result = await asyncio.to_thread(_exec)
    
    output = result.stdout.strip()
    error = result.stderr.strip()
    
    if result.returncode != 0:
        return f"PowerShell Error ({result.returncode}):\n{error}\n{output}"
        
    return output if output else (error if error else "Success (No Output)")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="list_tasks",
            description="List all scheduled tasks in the SovereignSpirit folder.",
            inputSchema={
                "type": "object",
                "properties": {},
            }
        ),
        Tool(
            name="create_task",
            description="Create a new scheduled task.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name of the task"},
                    "command": {"type": "string", "description": "Executable or script to run"},
                    "arguments": {"type": "string", "description": "Arguments for the command"},
                    "wake_seconds": {"type": "integer", "description": "Seconds from now to schedule (optional)", "default": 0},
                    "schedule_type": {"type": "string", "description": "Type of schedule (default: Once)", "default": "Once"},
                    "run_as_system": {"type": "boolean", "description": "If True, runs as SYSTEM (even if logged out). Requires Admin.", "default": False}
                },
                "required": ["name", "command", "arguments"]
            }
        ),
        Tool(
            name="get_task",
            description="Get detailed information about a scheduled task.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name of the task"}
                },
                "required": ["name"]
            }
        ),
        Tool(
            name="delete_task",
            description="Delete a scheduled task by name.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name of the task to delete"}
                },
                "required": ["name"]
            }
        ),
        Tool(
            name="schedule_wake",
            description="High-level helper to schedule a 'Wake Up' event for the Sovereign Spirit.",
            inputSchema={
                "type": "object",
                "properties": {
                    "seconds": {"type": "integer", "description": "How many seconds to sleep before waking"},
                },
                "required": ["seconds"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent | ImageContent | EmbeddedResource]:
    try:
        if name == "list_tasks":
            output = await run_powershell("Get-SovereignTasks | ConvertTo-Json -Depth 2")
            return [TextContent(type="text", text=output)]
            
        elif name == "get_task":
            task_name = arguments["name"].replace("'", "''")
            output = await run_powershell(f"Get-ScheduledTask -TaskName '{task_name}' -TaskPath '\\SovereignSpirit\\' | ConvertTo-Json")
            return [TextContent(type="text", text=output)]
            
        elif name == "create_task":
            # Sanitize inputs? PowerShell handles some, but we should be careful.
            # Using simple string interpolation for now, assuming trusted input from Spirit.
            # Ideally we'd pass args safely, but PS command strings are tricky.
            # We'll use single quotes for strings to minimize injection risks, escaping single quotes.
            
            task_name = arguments["name"].replace("'", "''")
            cmd = arguments["command"].replace("'", "''")
            args = arguments["arguments"].replace("'", "''")
            wake = arguments.get("wake_seconds", 0)
            run_as_system = arguments.get("run_as_system", False)
            ps_system = ":$true" if run_as_system else ":$false"
            
            ps_cmd = f"New-SovereignTask -Name '{task_name}' -Command '{cmd}' -Arguments '{args}' -WakeSecondsFromNow {wake} -RunAsSystem{ps_system}"
            output = await run_powershell(ps_cmd)
            return [TextContent(type="text", text=output)]
            
        elif name == "delete_task":
            task_name = arguments["name"].replace("'", "''")
            output = await run_powershell(f"Remove-SovereignTask -Name '{task_name}'")
            return [TextContent(type="text", text=output)]
            
        elif name == "schedule_wake":
            # This logic mimics the "Wake Up" protocol.
            # We assume the command to wake the spirit is running the entrypoint.
            # For now, let's assume valid command is 'python sentinel.py' or similar. 
            # Needs to be absolute path in production usually.
            
            seconds = arguments["seconds"]
            # Get absolute path to python and sentinel.py
            python_exe = sys.executable
            script_path = os.path.abspath("sentinel.py") # Or whichever entrypoint
            
            # Using arguments for New-SovereignTask
            # We use a specific task name
            task_name = "SovereignWakeCall"
            
            # First clean old one
            await run_powershell(f"Remove-SovereignTask -Name '{task_name}'")
            
            # Create new
            ps_cmd = f"New-SovereignTask -Name '{task_name}' -Command '{python_exe}' -Arguments '{script_path}' -WakeSecondsFromNow {seconds}"
            output = await run_powershell(ps_cmd)
            return [TextContent(type="text", text=f"Wake scheduled in {seconds} seconds. System output: {output}")]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        logger.error(f"Tool execution failed: {e}")
        return [TextContent(type="text", text=f"Error executing {name}: {str(e)}")]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
