"""
Tests for process_pending_task() with MCP single-shot tool call.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.core.heartbeat.pulse import process_pending_task
from src.core.llm_client import CompletionResponse

TASK = {"task_id": "t-001", "description": "Find information about Neo4j indexes"}


@pytest.mark.asyncio
async def test_act_with_tool_call():
    """ACT: agent calls a tool, result fed back, synthesis stored."""
    db = AsyncMock()
    graph = AsyncMock()
    graph.complete_task = AsyncMock(return_value=True)
    db.queue_response = AsyncMock()

    mock_agent = MagicMock()
    mock_agent.name = "Echo"
    mock_agent.designation = "Void Vessel"
    db.get_agent_state = AsyncMock(return_value=mock_agent)

    tool_response = CompletionResponse(
        content="",
        model="test",
        provider="lm_studio",
        tool_calls=[
            {
                "id": "call_1",
                "type": "function",
                "function": {
                    "name": "read_file",
                    "arguments": '{"path": "/app/README.md"}',
                },
            }
        ],
        finish_reason="tool_calls",
    )
    synthesis_response = CompletionResponse(
        content="I found that Neo4j uses B-tree indexes.",
        model="test",
        provider="lm_studio",
        tool_calls=[],
        finish_reason="stop",
    )

    with patch("src.core.heartbeat.pulse.get_llm_client") as mock_client_fn, patch(
        "src.core.heartbeat.pulse.get_mcp_manager"
    ) as mock_mcp_fn:
        mock_client = AsyncMock()
        mock_client.complete = AsyncMock(
            side_effect=[tool_response, synthesis_response]
        )
        mock_client_fn.return_value = mock_client

        mock_mcp = MagicMock()
        mock_mcp.get_tools_for_llm.return_value = [
            {"type": "function", "function": {"name": "read_file"}}
        ]
        mock_mcp.execute_tool = AsyncMock(return_value="# README content here")
        mock_mcp.available_tools = [
            {"name": "read_file", "server": "filesystem", "description": "Read a file"}
        ]
        mock_mcp_fn.return_value = mock_mcp

        result = await process_pending_task("echo", TASK, db, graph)

    assert result is True
    # Synthesis queued as response
    db.queue_response.assert_called_once()
    queued_content = db.queue_response.call_args[0][0].content
    assert "Neo4j" in queued_content


@pytest.mark.asyncio
async def test_act_without_tool_call():
    """ACT: agent responds directly without calling a tool."""
    db = AsyncMock()
    graph = AsyncMock()
    graph.complete_task = AsyncMock(return_value=True)
    db.queue_response = AsyncMock()

    mock_agent = MagicMock()
    mock_agent.name = "Echo"
    mock_agent.designation = "Void Vessel"
    db.get_agent_state = AsyncMock(return_value=mock_agent)

    direct_response = CompletionResponse(
        content="The task is complete. I have reviewed the configuration.",
        model="test",
        provider="lm_studio",
        tool_calls=[],
        finish_reason="stop",
    )

    with patch("src.core.heartbeat.pulse.get_llm_client") as mock_client_fn, patch(
        "src.core.heartbeat.pulse.get_mcp_manager"
    ) as mock_mcp_fn:
        mock_client = AsyncMock()
        mock_client.complete = AsyncMock(return_value=direct_response)
        mock_client_fn.return_value = mock_client

        mock_mcp = MagicMock()
        mock_mcp.get_tools_for_llm.return_value = []
        mock_mcp.available_tools = []
        mock_mcp_fn.return_value = mock_mcp

        result = await process_pending_task("echo", TASK, db, graph)

    assert result is True
    # complete() called only once (no tool loop)
    assert mock_client.complete.call_count == 1
