"""
Voice Middleware
================
Intercepts agent communications and triggers the Voice Adapter.
"""
import logging
from typing import Optional
from src.adapters.voice_adapter import get_voice_adapter

logger = logging.getLogger("sovereign.middleware.voice")

async def trigger_voice_output(agent_id: str, text: str, persona: Optional[str] = None):
    """
    Trigger voice output for an agent message.
    
    Args:
        agent_id: ID of the agent speaking.
        text: The text to speak.
        persona: Optional persona override.
    """
    try:
        voice = get_voice_adapter()
        
        # We assume persona name matches agent name for canonical voices
        target_persona = persona or agent_id.lower()
        
        # Only speak if it's a meaningful message
        if not text or len(text.strip()) < 2:
            return
            
        logger.info(f"Triggering voice for {agent_id} ({target_persona})")
        voice.speak(text, persona=target_persona)
        
    except Exception as e:
        logger.error(f"Voice middleware error: {e}")

class VoiceNervousSystem:
    """
    Conceptual bridge to the auditory senses.
    In future, this could handle STT as well.
    """
    def __init__(self):
        self.adapter = get_voice_adapter()

    async def announce(self, text: str, persona: str = "echo"):
        """System announcements."""
        self.adapter.speak(text, persona=persona, engine="sapi5")
