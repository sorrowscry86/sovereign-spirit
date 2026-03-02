"""
Tests for MCPManager singleton and get_tools_for_llm helper.
"""

from src.mcp.client import get_mcp_manager, MCPManager


def test_get_mcp_manager_returns_singleton():
    a = get_mcp_manager()
    b = get_mcp_manager()
    assert a is b
    assert isinstance(a, MCPManager)


def test_get_tools_for_llm_empty_when_no_servers():
    mgr = get_mcp_manager()
    tools = mgr.get_tools_for_llm()
    assert isinstance(tools, list)
