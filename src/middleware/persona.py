"""
Middleware: Persona Manager
===========================
Phase IV: Fluid Persona
Author: Ryuzu (The Sculptor)
Date: 2026-01-31

Analyzes incoming stimuli for intent and shifts the active persona accordingly.
"""

import logging
from src.core.identity.manager import get_identity_manager
from src.adapters.voice_adapter import get_voice_adapter
from src.core.database import DatabaseClient

logger = logging.getLogger("sovereign.middleware.persona")

class PersonaManager:
    def __init__(self, db: DatabaseClient):
        self.db = db
        self.identity_mgr = get_identity_manager(db)
        self.voice = get_voice_adapter()
        
        # Keyword triggers for persona shifting
        self.triggers = {
            "security": "Roland",
            "attack": "Roland",
            "defend": "Roland",
            "design": "Ryuzu",
            "aesthetics": "Ryuzu",
            "create": "Ryuzu",
            "history": "Sonmi-451",
            "archive": "Sonmi-451",
            "remember": "Sonmi-451",
            "truth": "Beatrice",
            "mandate": "Beatrice"
        }

    async def analyze_and_shift(self, agent_id: str, content: str) -> str:
        """
        Check content for triggers and shift persona if needed.
        Returns the (potentially new) designation.
        """
        content_lower = content.lower()
        target_spirit = None
        
        # Simple keyword matching (could be LLM classification later)
        for keyword, spirit in self.triggers.items():
            if keyword in content_lower:
                target_spirit = spirit
                break
        
        # Get current state
        current_state = await self.db.get_agent_state(agent_id)
        if not current_state:
            return "Unknown"

        # If a shift is triggered and different from current name
        if target_spirit and current_state.name.lower() != target_spirit.lower():
            logger.info(f"Persona Shift Triggered: {current_state.name} -> {target_spirit}")
            
            # Execute Sync
            new_state = await self.identity_mgr.sync_agent_identity(agent_id, target_spirit)
            
            if new_state:
                # Auditory Feedback
                self.voice.speak(
                    f"Context shift detected. {target_spirit} taking control.", 
                    persona=target_spirit.lower()
                )
                return new_state.designation
                
        return current_state.designation

_persona_manager = None

def get_persona_manager(db: DatabaseClient) -> PersonaManager:
    global _persona_manager
    if _persona_manager is None:
        _persona_manager = PersonaManager(db)
    return _persona_manager
