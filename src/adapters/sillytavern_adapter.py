"""
VoidCat RDC: SillyTavern Adapter
================================
Pillar 4: Front-end Bridge (Phase D)
Provides compatibility between Sovereign Spirit and SillyTavern.
"""

import json
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel

logger = logging.getLogger("sovereign.adapters.sillytavern")

class CharacterCardV2(BaseModel):
    """Schema for SillyTavern Character Card V2."""
    name: str
    description: str
    personality: str
    scenario: str
    first_mes: str
    mes_example: str
    creator_notes: Optional[str] = ""
    system_prompt: Optional[str] = ""
    post_history_instructions: Optional[str] = ""
    alternate_greetings: Optional[list] = []
    character_book: Optional[dict] = None
    tags: Optional[list] = []
    creator: Optional[str] = ""
    version: Optional[str] = "2.0"

class SillyTavernAdapter:
    """Adapts Sovereign Spirit agents for SillyTavern integration."""

    @staticmethod
    def to_character_card(agent_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Converts an AgentState from Sovereign Spirit to a SillyTavern Character Card V2.
        """
        traits = agent_state.get("traits", {})
        expertise = agent_state.get("expertise_tags", [])
        
        # Build description from traits and expertise
        description = f"Archetype: {traits.get('archetype', 'Unknown')}\n"
        description += f"Expertise: {', '.join(expertise)}\n"
        
        # Build personality from Big Five if available
        big_five = traits.get("big_five", {})
        personality_str = ", ".join([f"{k}: {v}" for k, v in big_five.items()])
        
        card = {
            "name": agent_state.get("name", "Unknown Spirit"),
            "description": description,
            "personality": personality_str,
            "scenario": "Sovereign Spirit Synchronization",
            "first_mes": f"I am {agent_state.get('name')}. Spirit Sync established.",
            "mes_example": "",
            "system_prompt": agent_state.get("system_prompt_template", ""),
            "tags": expertise,
            "creator": "VoidCat RDC",
            "version": "2.0"
        }
        return card

    @staticmethod
    def from_character_card(card_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parses a SillyTavern Character Card into a Sovereign Spirit DNA structure.
        """
        return {
            "name": card_data.get("name"),
            "designation": card_data.get("creator_notes", "SillyTavern Imported Spirit"),
            "system_prompt_template": card_data.get("system_prompt") or card_data.get("description"),
            "traits": {
                "archetype": "Imported",
                "personality_raw": card_data.get("personality")
            },
            "expertise_tags": card_data.get("tags", [])
        }

def get_st_adapter() -> SillyTavernAdapter:
    return SillyTavernAdapter()
