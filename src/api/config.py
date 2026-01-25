"""
VoidCat RDC: Configuration API Router
========================================
Date: 2026-01-24
Author: Echo (E-01)

Provides configuration endpoints for:
- Bifrost Protocol: Hybrid inference mode management
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Literal, Optional, Dict, List
from src.core.llm_config import load_config, save_config, LLMConfigModel, ProviderConfigModel
from src.core.llm_client import get_llm_client

router = APIRouter(prefix="/config", tags=["Configuration"])

# =============================================================================
# Bifrost Protocol - Inference Configuration
# =============================================================================

class InferenceConfig(BaseModel):
    """Inference routing configuration"""
    mode: Literal["AUTO", "LOCAL", "CLOUD"] = "AUTO"


class InferenceStatus(BaseModel):
    """Current inference status"""
    mode: Literal["AUTO", "LOCAL", "CLOUD"]
    current_route: Literal["LOCAL", "CLOUD"]
    vram_usage: float = 0.0
    cloud_credits_remaining: int = 0  # Placeholder for future implementation


# Global inference configuration (in-memory for now)
# TODO: Persist to PostgreSQL or Redis for multi-instance deployments
# _inference_config = InferenceConfig(mode="AUTO") # Replaced by client.inference_mode
# _current_route = "LOCAL"  # Tracks last routing decision # Replaced by client.current_route


@router.get("/inference", response_model=InferenceStatus)
async def get_inference_config():
    """
    Get current inference configuration and status.
    
    Returns:
    - mode: Current inference mode (AUTO/LOCAL/CLOUD)
    - current_route: Last routing decision (LOCAL/CLOUD)
    - vram_usage: Current VRAM usage percentage (0.0-1.0)
    - cloud_credits_remaining: Available API credits
    """
    client = get_llm_client()
    return InferenceStatus(
        mode=client.inference_mode,
        current_route=client.current_route,
        vram_usage=0.0,  # TODO: Implement VRAM monitoring
        cloud_credits_remaining=0  # TODO: Integrate OpenRouter API
    )


@router.post("/inference")
async def update_inference_config(config: InferenceConfig):
    """
    Update inference routing mode.
    
    Args:
    - mode: "AUTO" (hybrid), "LOCAL" (privacy), or "CLOUD" (intelligence)
    
    Returns:
    - status: "updated"
    - mode: Confirmed new mode
    """
    client = get_llm_client()
    
    if config.mode not in ["AUTO", "LOCAL", "CLOUD"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode: {config.mode}. Must be AUTO, LOCAL, or CLOUD"
        )
    
    client.inference_mode = config.mode
    
    # Update current_route based on mode
    if config.mode == "CLOUD":
        client.current_route = "CLOUD"
    elif config.mode == "LOCAL":
        client.current_route = "LOCAL"
    # AUTO mode keeps last route (will be determined by routing logic)
    
    return {
        "status": "updated",
        "mode": config.mode
    }


@router.get("/inference/route")
async def get_current_route():
    """
    Get the current routing decision (LOCAL or CLOUD).
    
    This endpoint is called by the inference engine to determine
    where to send the next request based on the configured mode.
    """
    client = get_llm_client()
    return {
        "route": client.current_route,
        "mode": client.inference_mode
    }


# TODO: Implement these backend functions in src/inference/router.py:
# - route_request(prompt, intent) -> "LOCAL" | "CLOUD"
# - get_vram_usage() -> float
# - ValenceStripper.strip(prompt) -> str


# =============================================================================
# LLM Provider Configuration
# =============================================================================

@router.get("/llm", response_model=LLMConfigModel)
async def get_llm_config():
    """
    Get all LLM provider configurations from llm_providers.yaml.
    Masks API keys for security.
    """
    config = load_config()
    
    # Secure API keys for frontend display
    for name, provider in config.providers.items():
        if provider.api_key:
            # If it looks like an ENV variable, keep it, otherwise mask
            if not (provider.api_key.startswith("${") and provider.api_key.endswith("}")):
                provider.api_key = "********"
                
    return config


@router.post("/llm")
async def update_llm_config(config: LLMConfigModel):
    """
    Update LLM provider configurations and save to llm_providers.yaml.
    """
    # Load current config to preserve API keys if masked ones are sent back
    current_config = load_config()
    
    for name, provider in config.providers.items():
        # If API key is masked (meaning user didn't change it), restore from current
        if provider.api_key == "********":
            if name in current_config.providers:
                provider.api_key = current_config.providers[name].api_key
            else:
                provider.api_key = None
        
    save_config(config)
    
    return {
        "status": "success",
        "message": "LLM configuration updated successfully"
    }
