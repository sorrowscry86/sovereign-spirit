import asyncio
import logging
from typing import Dict, List, Any, Optional
from contextlib import AsyncExitStack

# Requires: pip install mcp
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from src.mcp.config import get_server_config

logger = logging.getLogger("sovereign.mcp")


class MCPManager:
    """
    The Hands of the Ghost.
    Manages connections to local MCP servers and routes tool execution.
    """

    def __init__(self):
        self.sessions: Dict[str, ClientSession] = {}
        self.exit_stack = AsyncExitStack()
        self.available_tools: List[Dict] = []

    async def connect_server(self, server_name: str):
        """Spawns an MCP server and connects via stdio."""
        config = get_server_config(server_name)
        if not config:
            logger.error(f"MCP Server '{server_name}' not found in registry.")
            return

        logger.info(f"Connecting to MCP Server: {server_name}...")

        server_params = StdioServerParameters(
            command=config["command"], args=config["args"], env=config.get("env")
        )

        try:
            # Establish the transport and session using the official Python SDK
            read, write = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            )

            await session.initialize()
            self.sessions[server_name] = session

            # Aggregate tools immediately upon connection
            # We list them so the LLM knows what it can do
            tools_result = await session.list_tools()
            for tool in tools_result.tools:
                # Cache the tool definition so the LLM knows what it can do
                self.available_tools.append(
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "server": server_name,
                        "schema": tool.inputSchema,
                    }
                )

            logger.info(
                f"Connected to {server_name}. Loaded {len(tools_result.tools)} tools."
            )

        except Exception as e:
            logger.error(f"Failed to connect to MCP server {server_name}: {e}")
            raise e

    async def execute_tool(
        self, server_name: str, tool_name: str, arguments: Dict[str, Any]
    ) -> str:
        """Executes a tool on the specified server."""
        if server_name not in self.sessions:
            return f"Error: Server {server_name} not connected."

        try:
            session = self.sessions[server_name]
            result = await session.call_tool(tool_name, arguments)

            # MCP returns a list of content blocks (Text or Image)
            # We squash them into a single string for the LLM to read
            output_text = []
            for content in result.content:
                if content.type == "text":
                    output_text.append(content.text)
                # Future: Handle images if the Spirit gains sight

            return "\n".join(output_text)

        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return f"Error executing {tool_name}: {str(e)}"

    def get_tools_for_llm(self) -> List[Dict]:
        """Return available tools in OpenAI function-call format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["schema"],
                },
            }
            for t in self.available_tools
        ]

    async def disconnect_server(self, server_name: str) -> bool:
        """Disconnect a specific MCP server and remove its tools."""
        if server_name not in self.sessions:
            return False

        # Remove tools from this server
        self.available_tools = [
            t for t in self.available_tools if t.get("server") != server_name
        ]

        # Close session (best-effort)
        try:
            del self.sessions[server_name]
        except Exception as e:
            logger.warning(f"Error disconnecting {server_name}: {e}")

        logger.info(f"Disconnected MCP server: {server_name}")
        return True

    async def shutdown(self):
        """Gracefully closes all tool connections."""
        logger.info("Severing MCP connections...")
        await self.exit_stack.aclose()


# =============================================================================
# Singleton
# =============================================================================

_mcp_manager: Optional[MCPManager] = None


def get_mcp_manager() -> MCPManager:
    """Get or create the singleton MCPManager."""
    global _mcp_manager
    if _mcp_manager is None:
        _mcp_manager = MCPManager()
    return _mcp_manager


async def shutdown_mcp_manager() -> None:
    """Gracefully close all MCP server connections."""
    global _mcp_manager
    if _mcp_manager is not None:
        await _mcp_manager.shutdown()
        _mcp_manager = None
