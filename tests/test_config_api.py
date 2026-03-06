"""Tests for config API endpoints — LLM health check and test reply."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_health_check_single_provider():
    """GET /config/llm/health/{name} returns health for one provider."""
    from src.api.config import get_llm_health_single

    with patch("src.api.config.get_llm_client") as mock_get:
        client = MagicMock()
        client.providers = {
            "lm_studio": MagicMock(
                provider_type=MagicMock(value="lm_studio"),
                model="auto",
                endpoint="http://localhost:1234/v1",
            )
        }
        client.health_check = AsyncMock(return_value=True)
        mock_get.return_value = client

        result = await get_llm_health_single("lm_studio")
        assert result["online"] is True
        assert result["name"] == "lm_studio"
        assert result["type"] == "lm_studio"


@pytest.mark.asyncio
async def test_health_check_unknown_provider():
    """GET /config/llm/health/{name} returns 404 for unknown provider."""
    from src.api.config import get_llm_health_single

    with patch("src.api.config.get_llm_client") as mock_get:
        client = MagicMock()
        client.providers = {}
        mock_get.return_value = client

        with pytest.raises(HTTPException) as exc_info:
            await get_llm_health_single("nonexistent")
        assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_health_check_offline_provider():
    """GET /config/llm/health/{name} returns online=false when health check fails."""
    from src.api.config import get_llm_health_single

    with patch("src.api.config.get_llm_client") as mock_get:
        client = MagicMock()
        client.providers = {
            "openrouter": MagicMock(
                provider_type=MagicMock(value="openrouter"),
                model="mimo-v2-flash",
                endpoint="https://openrouter.ai/api/v1",
            )
        }
        client.health_check = AsyncMock(return_value=False)
        mock_get.return_value = client

        result = await get_llm_health_single("openrouter")
        assert result["online"] is False
        assert result["name"] == "openrouter"


@pytest.mark.asyncio
async def test_test_reply_success():
    """POST /config/llm/test/{name} sends test prompt and returns response."""
    from src.api.config import test_llm_provider

    with patch("src.api.config.get_llm_client") as mock_get:
        client = MagicMock()
        client.providers = {"lm_studio": MagicMock()}
        resp = MagicMock()
        resp.content = "Hello! I'm working."
        resp.model = "qwen3-4b"
        resp.provider = "lm_studio"
        resp.tokens_used = 10
        client.complete = AsyncMock(return_value=resp)
        mock_get.return_value = client

        result = await test_llm_provider("lm_studio")
        assert result["success"] is True
        assert "Hello" in result["response"]
        assert result["model"] == "qwen3-4b"


@pytest.mark.asyncio
async def test_test_reply_failure():
    """POST /config/llm/test/{name} returns error on LLM failure."""
    from src.api.config import test_llm_provider

    with patch("src.api.config.get_llm_client") as mock_get:
        client = MagicMock()
        client.providers = {"openrouter": MagicMock()}
        client.complete = AsyncMock(side_effect=RuntimeError("Connection refused"))
        mock_get.return_value = client

        result = await test_llm_provider("openrouter")
        assert result["success"] is False
        assert "Connection refused" in result["error"]


@pytest.mark.asyncio
async def test_test_reply_unknown_provider():
    """POST /config/llm/test/{name} returns 404 for unknown provider."""
    from src.api.config import test_llm_provider

    with patch("src.api.config.get_llm_client") as mock_get:
        client = MagicMock()
        client.providers = {}
        mock_get.return_value = client

        with pytest.raises(HTTPException) as exc_info:
            await test_llm_provider("nonexistent")
        assert exc_info.value.status_code == 404
