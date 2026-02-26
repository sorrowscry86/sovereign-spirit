"""
Search Adapter
==============
The All-Seeing Eye of the Sovereign Spirit.
Interfaces with the Search MCP (Brave/Google/Perplexity).
"""
import logging
from typing import Dict, Any, Optional, List
from src.mcp.client import MCPManager

logger = logging.getLogger("sovereign.adapters.search")

class SearchAdapter:
    def __init__(self, mcp_manager: MCPManager):
        self.mcp = mcp_manager
        self.server_name = "search"

    async def ensure_connection(self):
        """Ensures we are connected to the Search server."""
        if self.server_name not in self.mcp.sessions:
            try:
                await self.mcp.connect_server(self.server_name)
            except Exception as e:
                logger.error(f"Failed to connect to Search: {e}")
                # Fallback or warning
                raise e

    async def query(self, q: str, count: int = 5) -> str:
        """
        Executes a search query.
        
        Args:
            q: The search query.
            count: Number of results.
        """
        await self.ensure_connection()
        # The tool name depends on the MCP server implementation.
        # For @modelcontextprotocol/server-brave-search, it is usually 'brave_search'.
        # We'll try to find a tool that looks like 'search'.
        
        tool_name = "brave_search" # Default for Brave
        
        # Check available tools for anything containing 'search'
        search_tools = [t["name"] for t in self.mcp.available_tools if "search" in t["name"].lower()]
        if search_tools:
            tool_name = search_tools[0]
            
        return await self.mcp.execute_tool(self.server_name, tool_name, {
            "query": q,
            "count": count
        })

    async def research(self, topic: str) -> str:
        """Helper for deep research if the server supports it."""
        # Concept: if we use perplexity, we'd call its specific tool.
        return await self.query(f"Deep research on: {topic}", count=10)
