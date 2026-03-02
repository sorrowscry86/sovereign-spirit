"""
VoidCat RDC: Sovereign Spirit - LLM Configuration
==================================================
Version: 1.1.0
Author: Echo (E-01)
Date: 2026-01-23

Configuration management for LLM providers with YAML persistence.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

import yaml
from pydantic import BaseModel, Field

from src.core.llm_client import ProviderConfig, ProviderType, LLMClient, get_llm_client

logger = logging.getLogger("sovereign.llm.config")

# =============================================================================
# Configuration Models
# =============================================================================


class ProviderConfigModel(BaseModel):
    """Pydantic model for provider configuration in YAML."""

    type: str
    endpoint: str
    model: str
    api_key: Optional[str] = None
    max_tokens: int = 150
    temperature: float = 0.7
    timeout: float = 30.0


class LLMConfigModel(BaseModel):
    """Root configuration model for LLM providers."""

    active_provider: str = "ollama_local"
    fallback_chain: List[str] = Field(
        default_factory=lambda: ["ollama_local", "lm_studio", "openrouter"]
    )
    providers: Dict[str, ProviderConfigModel] = Field(default_factory=dict)


# =============================================================================
# Configuration Path
# =============================================================================


def get_config_path() -> Path:
    """Get the path to the LLM providers config file."""
    config_dir = Path(os.getenv("SOVEREIGN_CONFIG_DIR", "config"))
    return config_dir / "llm_providers.yaml"


# =============================================================================
# Configuration Loading/Saving
# =============================================================================


def load_config() -> LLMConfigModel:
    """Load LLM configuration from YAML file."""
    config_path = get_config_path()

    if not config_path.exists():
        logger.info(f"Config file not found, using defaults: {config_path}")
        return LLMConfigModel()

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        # Expand environment variables and VoidKey relay fallback
        if "providers" in data:
            try:
                from src.core.voidkey_client import get_vk_key as _get_vk_key
            except ImportError:
                _get_vk_key = None

            for name, provider in data["providers"].items():
                if "api_key" in provider and provider["api_key"]:
                    api_key = provider["api_key"]
                    if api_key.startswith("${") and api_key.endswith("}"):
                        env_var = api_key[2:-1]
                        # Try environment first
                        val = os.getenv(env_var)
                        if not val and _get_vk_key is not None:
                            # Fallback to VoidKey Relay
                            logger.info(
                                f"Env var {env_var} not found, checking VoidKey Relay..."
                            )
                            val = _get_vk_key(env_var)

                        provider["api_key"] = val

        return LLMConfigModel(**data)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return LLMConfigModel()


def save_config(config: LLMConfigModel) -> None:
    """Save LLM configuration to YAML file."""
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert to dict, keeping env var placeholders for api_keys
    data = config.model_dump()

    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    logger.info(f"Config saved to: {config_path}")


def apply_config_to_client(
    config: LLMConfigModel, client: Optional[LLMClient] = None
) -> LLMClient:
    """Apply configuration to LLM client."""
    client = client or get_llm_client()

    # Update providers from config
    for name, provider_config in config.providers.items():
        provider = ProviderConfig(
            name=name,
            provider_type=ProviderType(provider_config.type),
            endpoint=provider_config.endpoint,
            model=provider_config.model,
            api_key=provider_config.api_key,
            max_tokens=provider_config.max_tokens,
            temperature=provider_config.temperature,
            timeout=provider_config.timeout,
        )
        client.add_provider(provider)

    # Set active provider and fallback chain
    if config.active_provider in client.providers:
        client.set_active_provider(config.active_provider)

    client.fallback_chain = config.fallback_chain

    return client


def initialize_llm_from_config() -> LLMClient:
    """Load config and initialize LLM client."""
    config = load_config()
    return apply_config_to_client(config)
