"""
Tests for MUSE prompt extensions: project context and PONDER state.
"""

import pytest
from src.core.heartbeat.pulse import generate_micro_thought
from src.core.llm_client import CompletionResponse
from unittest.mock import AsyncMock, patch

STATUS_IDLE = {
    "name": "Echo",
    "designation": "The Void Vessel",
    "status": "idle",
    "last_active": "2m ago",
    "pending_count": 0,
    "pending_tasks": [],
    "unread_count": 0,
    "last_message": "None",
    "active_project": None,
}


@pytest.mark.asyncio
async def test_muse_returns_ponder_when_model_says_ponder():
    ponder_response = CompletionResponse(
        content="PONDER",
        model="test",
        provider="test",
        tool_calls=[],
        finish_reason="stop",
    )
    with patch("src.core.heartbeat.pulse.get_llm_client") as mock_fn:
        mock_client = AsyncMock()
        mock_client.complete = AsyncMock(return_value=ponder_response)
        mock_fn.return_value = mock_client
        action, details = await generate_micro_thought(STATUS_IDLE)
    assert action == "PONDER"


@pytest.mark.asyncio
async def test_muse_includes_project_context_when_active():
    status_with_project = {
        **STATUS_IDLE,
        "active_project": {
            "title": "Refactor DB layer",
            "progress_notes": "Step 1 done.\n",
        },
    }
    with patch("src.core.heartbeat.pulse.get_llm_client") as mock_fn:
        mock_client = AsyncMock()
        mock_client.complete = AsyncMock(
            return_value=CompletionResponse(
                content="ACT: Continue DB refactor",
                model="t",
                provider="t",
                tool_calls=[],
                finish_reason="stop",
            )
        )
        mock_fn.return_value = mock_client
        await generate_micro_thought(status_with_project)
        # Verify project title was in the prompt
        call_args = mock_client.complete.call_args
        system_msg = call_args[1]["messages"][0].content
        assert "Refactor DB layer" in system_msg
