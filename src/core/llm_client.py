"""
VoidCat RDC: Sovereign Spirit - Unified LLM Client
===================================================
Version: 1.1.0
Author: Echo (E-01)
Date: 2026-01-23

Unified async client supporting multiple OpenAI-compatible LLM providers.
Supports: Ollama, LM Studio, OpenRouter, OpenAI, Anthropic (via OpenRouter)
"""

import os
import logging
import asyncio
from typing import Optional, List, Dict, Any, AsyncIterator
from dataclasses import dataclass
from enum import Enum

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger("sovereign.llm")

# =============================================================================
# Provider Types
# =============================================================================

class ProviderType(str, Enum):
    """Supported LLM provider types."""
    OLLAMA = "ollama"
    LM_STUDIO = "lm_studio"
    OPENROUTER = "openrouter"
    OPENAI = "openai"


@dataclass
class ProviderConfig:
    """Configuration for an LLM provider."""
    name: str
    provider_type: ProviderType
    endpoint: str
    model: str
    api_key: Optional[str] = None
    max_tokens: int = 150
    temperature: float = 0.7
    timeout: float = 30.0


# =============================================================================
# Default Provider Configurations
# =============================================================================

DEFAULT_PROVIDERS: Dict[str, ProviderConfig] = {
    "ollama_local": ProviderConfig(
        name="ollama_local",
        provider_type=ProviderType.OLLAMA,
        endpoint=os.getenv("OLLAMA_HOST", "http://localhost:11434") + "/v1",
        model=os.getenv("OLLAMA_MODEL", "mistral:7b-instruct-v0.2-q4_K_M"),
    ),
    "lm_studio": ProviderConfig(
        name="lm_studio",
        provider_type=ProviderType.LM_STUDIO,
        endpoint=os.getenv("LM_STUDIO_HOST", "http://localhost:1234") + "/v1",
        model="auto",  # LM Studio uses the currently loaded model
    ),
    "openrouter": ProviderConfig(
        name="openrouter",
        provider_type=ProviderType.OPENROUTER,
        endpoint="https://openrouter.ai/api/v1",
        model=os.getenv("OPENROUTER_MODEL", "mistralai/mistral-7b-instruct"),
        api_key=os.getenv("OPENROUTER_API_KEY"),
    ),
    "openai": ProviderConfig(
        name="openai",
        provider_type=ProviderType.OPENAI,
        endpoint="https://api.openai.com/v1",
        model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
        api_key=os.getenv("OPENAI_API_KEY"),
    ),
}


# =============================================================================
# Request/Response Models
# =============================================================================

class ChatMessage(BaseModel):
    """A single chat message."""
    role: str = Field(..., pattern="^(system|user|assistant)$")
    content: str


class CompletionRequest(BaseModel):
    """Request for chat completion."""
    messages: List[ChatMessage]
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    stream: bool = False


class CompletionResponse(BaseModel):
    """Response from chat completion."""
    content: str
    model: str
    provider: str
    tokens_used: Optional[int] = None
    finish_reason: Optional[str] = None


# =============================================================================
# Unified LLM Client
# =============================================================================

class LLMClient:
    """
    Unified async client for OpenAI-compatible LLM providers.
    
    Supports automatic fallback between providers when one fails.
    """
    
    def __init__(
        self,
        providers: Optional[Dict[str, ProviderConfig]] = None,
        active_provider: str = "ollama_local",
        fallback_chain: Optional[List[str]] = None,
    ):
        self.providers = providers or DEFAULT_PROVIDERS.copy()
        self.active_provider = active_provider
        self.fallback_chain = fallback_chain or ["ollama_local", "lm_studio", "openrouter"]
        self._client = httpx.AsyncClient(timeout=60.0)
    
    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
    
    def get_provider(self, name: Optional[str] = None) -> ProviderConfig:
        """Get provider configuration by name."""
        provider_name = name or self.active_provider
        if provider_name not in self.providers:
            raise ValueError(f"Unknown provider: {provider_name}")
        return self.providers[provider_name]
    
    def set_active_provider(self, name: str) -> None:
        """Set the active provider."""
        if name not in self.providers:
            raise ValueError(f"Unknown provider: {name}")
        self.active_provider = name
        logger.info(f"Active LLM provider set to: {name}")
    
    def add_provider(self, config: ProviderConfig) -> None:
        """Add or update a provider configuration."""
        self.providers[config.name] = config
        logger.info(f"Provider added/updated: {config.name}")
    
    async def health_check(self, provider_name: Optional[str] = None) -> bool:
        """Check if a provider is available."""
        config = self.get_provider(provider_name)
        try:
            # For OpenAI-compatible APIs, check /models endpoint
            url = f"{config.endpoint}/models"
            headers = self._build_headers(config)
            response = await self._client.get(url, headers=headers, timeout=5.0)
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"Health check failed for {config.name}: {e}")
            return False
    
    async def complete(
        self,
        messages: List[ChatMessage],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        provider_name: Optional[str] = None,
        use_fallback: bool = True,
    ) -> CompletionResponse:
        """
        Generate a chat completion.
        
        Args:
            messages: List of chat messages
            max_tokens: Override max tokens
            temperature: Override temperature
            provider_name: Specific provider to use
            use_fallback: Try fallback providers on failure
        
        Returns:
            CompletionResponse with generated content
        """
        providers_to_try = [provider_name] if provider_name else (
            [self.active_provider] + [p for p in self.fallback_chain if p != self.active_provider]
            if use_fallback else [self.active_provider]
        )
        
        last_error = None
        for p_name in providers_to_try:
            if p_name not in self.providers:
                continue
            try:
                return await self._complete_with_provider(
                    p_name, messages, max_tokens, temperature
                )
            except Exception as e:
                logger.warning(f"Provider {p_name} failed: {e}")
                last_error = e
        
        raise RuntimeError(f"All providers failed. Last error: {last_error}")
    
    async def _complete_with_provider(
        self,
        provider_name: str,
        messages: List[ChatMessage],
        max_tokens: Optional[int],
        temperature: Optional[float],
    ) -> CompletionResponse:
        """Execute completion with a specific provider."""
        config = self.get_provider(provider_name)
        
        url = f"{config.endpoint}/chat/completions"
        headers = self._build_headers(config)
        
        payload = {
            "model": config.model,
            "messages": [m.model_dump() for m in messages],
            "max_tokens": max_tokens or config.max_tokens,
            "temperature": temperature if temperature is not None else config.temperature,
            "stream": False,
        }
        
        response = await self._client.post(
            url, json=payload, headers=headers, timeout=config.timeout
        )
        response.raise_for_status()
        
        data = response.json()
        choice = data["choices"][0]
        
        return CompletionResponse(
            content=choice["message"]["content"],
            model=data.get("model", config.model),
            provider=provider_name,
            tokens_used=data.get("usage", {}).get("total_tokens"),
            finish_reason=choice.get("finish_reason"),
        )
    
    async def complete_streaming(
        self,
        messages: List[ChatMessage],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        provider_name: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """
        Generate a streaming chat completion.
        
        Yields content chunks as they arrive.
        """
        config = self.get_provider(provider_name)
        
        url = f"{config.endpoint}/chat/completions"
        headers = self._build_headers(config)
        
        payload = {
            "model": config.model,
            "messages": [m.model_dump() for m in messages],
            "max_tokens": max_tokens or config.max_tokens,
            "temperature": temperature if temperature is not None else config.temperature,
            "stream": True,
        }
        
        async with self._client.stream(
            "POST", url, json=payload, headers=headers, timeout=config.timeout
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        import json
                        chunk = json.loads(data)
                        delta = chunk["choices"][0].get("delta", {})
                        if "content" in delta:
                            yield delta["content"]
                    except Exception:
                        continue
    
    def _build_headers(self, config: ProviderConfig) -> Dict[str, str]:
        """Build request headers for a provider."""
        headers = {"Content-Type": "application/json"}
        
        if config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"
        
        # OpenRouter requires additional headers
        if config.provider_type == ProviderType.OPENROUTER:
            headers["HTTP-Referer"] = "https://voidcat.org"
            headers["X-Title"] = "Sovereign Spirit"
        
        return headers


# =============================================================================
# Singleton Instance
# =============================================================================

_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get or create the singleton LLM client."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client


async def shutdown_llm_client() -> None:
    """Shutdown the singleton LLM client."""
    global _llm_client
    if _llm_client:
        await _llm_client.close()
        _llm_client = None
