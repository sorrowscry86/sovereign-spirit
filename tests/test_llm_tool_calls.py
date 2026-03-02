"""
Tests for LLMClient tool_calls support.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.core.llm_client import LLMClient, ChatMessage, CompletionResponse

FAKE_TOOL = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
            },
        },
    }
]

FAKE_TOOL_RESPONSE = {
    "choices": [
        {
            "message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_abc",
                        "type": "function",
                        "function": {
                            "name": "read_file",
                            "arguments": '{"path": "/app/test.txt"}',
                        },
                    }
                ],
            },
            "finish_reason": "tool_calls",
        }
    ],
    "model": "test-model",
    "usage": {"total_tokens": 50},
}


@pytest.mark.asyncio
async def test_complete_returns_tool_calls():
    client = LLMClient()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = FAKE_TOOL_RESPONSE
    mock_response.raise_for_status = MagicMock()

    with patch.object(client._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        result = await client.complete(
            messages=[ChatMessage(role="user", content="read the file")],
            tools=FAKE_TOOL,
            provider_name="lm_studio",
        )

    assert result.tool_calls != []
    assert result.tool_calls[0]["function"]["name"] == "read_file"
    assert result.finish_reason == "tool_calls"


@pytest.mark.asyncio
async def test_complete_without_tools_unchanged():
    """Existing call sites still work with no tools argument."""
    client = LLMClient()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {"content": "hello", "tool_calls": []},
                "finish_reason": "stop",
            }
        ],
        "model": "test-model",
        "usage": {"total_tokens": 10},
    }
    mock_response.raise_for_status = MagicMock()

    with patch.object(client._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        result = await client.complete(
            messages=[ChatMessage(role="user", content="hi")],
            provider_name="lm_studio",
        )

    assert result.tool_calls == []
    assert result.content == "hello"
