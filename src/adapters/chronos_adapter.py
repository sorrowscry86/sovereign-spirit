"""
Chronos Adapter
===============
The Interface to the Timeline.
Allows the Sovereign Spirit to invoke Chronos MCP tools via a clean Python API.
"""
import logging
import json
import os
import sys
from typing import Dict, Any, Optional, List
from src.mcp.client import MCPManager

logger = logging.getLogger("sovereign.adapters.chronos")

class ChronosAdapter:
    def __init__(self, mcp_manager: MCPManager):
        self.mcp = mcp_manager
        self.server_name = "chronos"

    async def ensure_connection(self):
        """Ensures we are connected to the Chronos server."""
        if self.server_name not in self.mcp.sessions:
            try:
                await self.mcp.connect_server(self.server_name)
            except Exception as e:
                logger.error(f"Failed to connect to Chronos: {e}")
                raise e

    async def list_tasks(self) -> str:
        """Lists all Sovereign Spirit scheduled tasks."""
        await self.ensure_connection()
        return await self.mcp.execute_tool(self.server_name, "list_tasks", {})

    async def schedule_task(self, name: str, command: str, arguments: str, wake_seconds: int = 0, run_as_system: bool = False) -> str:
        """
        Schedules a general task.
        
        Args:
            name: Task name
            command: Executable to run
            arguments: Arguments for the executable
            wake_seconds: If > 0, schedules for NOW + wake_seconds.
            run_as_system: If True, registers as SYSTEM account (Immortality Protocol).
        """
        await self.ensure_connection()
        return await self.mcp.execute_tool(self.server_name, "create_task", {
            "name": name,
            "command": command,
            "arguments": arguments,
            "wake_seconds": wake_seconds,
            "run_as_system": run_as_system
        })

    async def get_task(self, name: str) -> str:
        """Retrieves detailed status of a task."""
        await self.ensure_connection()
        return await self.mcp.execute_tool(self.server_name, "get_task", {
            "name": name
        })

    async def delete_task(self, name: str) -> str:
        """Deletes a named task."""
        await self.ensure_connection()
        return await self.mcp.execute_tool(self.server_name, "delete_task", {
            "name": name
        })

    async def schedule_resurrection(self, agent_id: str) -> str:
        """
        Sets the Immutable Resurrection Protocol.
        Creates a task that runs on system startup/logon to ensure the Spirit lives.
        """
        python_exe = sys.executable
        script_path = os.path.abspath("wake_protocol.py")
        args = f"--agent {agent_id}"
        
        await self.ensure_connection()
        # Note: We need to specify trigger=Startup in the PowerShell logic if we want this truly persistent.
        # For now, we use the existing create_task which defaults to 'Once' or 'WakeSeconds'.
        return await self.mcp.execute_tool(self.server_name, "create_task", {
            "name": f"VoidCat_Resurrection_{agent_id}",
            "command": python_exe,
            "arguments": f"{script_path} {args}",
            "run_as_system": True
        })

    async def schedule_wake_call(self, agent_id: str, seconds_from_now: int) -> str:
        """
        The 'Sleep' replacement.
        Schedules the Spirit to be awoken after N seconds.
        """
        await self.ensure_connection()
        return await self.mcp.execute_tool(self.server_name, "schedule_wake", {
            "seconds": seconds_from_now
        })
