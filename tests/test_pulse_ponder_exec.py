"""
Tests for PONDER execution: Prism retrieval + behavior dispatch.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.core.heartbeat.pulse import execute_ponder
from src.core.llm_client import CompletionResponse

STATUS = {
    "agent_id": "echo",
    "name": "Echo",
    "designation": "The Void Vessel",
    "last_message": "Testing...",
}


@pytest.mark.asyncio
async def test_ponder_reflect_writes_to_memory():
    ponder_response = CompletionResponse(
        content="BEHAVIOR: REFLECT\nTARGET: none\nCONTENT: I have been thinking about the nature of recursion.",
        model="test",
        provider="test",
        tool_calls=[],
        finish_reason="stop",
    )
    db = AsyncMock()
    with patch("src.core.heartbeat.pulse.get_llm_client") as mock_llm, patch(
        "src.core.heartbeat.pulse._get_prism_context", new_callable=AsyncMock
    ) as mock_prism, patch(
        "src.core.heartbeat.pulse._store_ponder_memory", new_callable=AsyncMock
    ) as mock_store:

        mock_client = AsyncMock()
        mock_client.complete = AsyncMock(return_value=ponder_response)
        mock_llm.return_value = mock_client
        mock_prism.return_value = "Recent memory: nothing."

        result = await execute_ponder(STATUS, db)

    assert result == (
        "PONDER",
        "REFLECT: I have been thinking about the nature of recursion.",
    )
    mock_store.assert_called_once()


@pytest.mark.asyncio
async def test_ponder_socialize_queues_message():
    ponder_response = CompletionResponse(
        content="BEHAVIOR: SOCIALIZE\nTARGET: Ryuzu\nCONTENT: Hey Ryuzu, have you considered the implications of async task dispatch?",
        model="test",
        provider="test",
        tool_calls=[],
        finish_reason="stop",
    )
    db = AsyncMock()
    db.queue_response = AsyncMock()
    with patch("src.core.heartbeat.pulse.get_llm_client") as mock_llm, patch(
        "src.core.heartbeat.pulse._get_prism_context", new_callable=AsyncMock
    ) as mock_prism, patch(
        "src.core.heartbeat.pulse._store_ponder_memory", new_callable=AsyncMock
    ):

        mock_client = AsyncMock()
        mock_client.complete = AsyncMock(return_value=ponder_response)
        mock_llm.return_value = mock_client
        mock_prism.return_value = "Nothing."

        await execute_ponder(STATUS, db)

    db.queue_response.assert_called_once()
