"""
Voice Adapter
=============
The Vocal Chords of the Sovereign Spirit.
Interfaces with the VoiceVessel project to provide TTS capabilities.
"""
import logging
import subprocess
import os
from typing import Optional

logger = logging.getLogger("sovereign.adapters.voice")

class VoiceAdapter:
    """
    Adapter for VoiceVessel integration.
    Allows the Spirit to speak using various engines/personas.
    """
    
    def __init__(self):
        # Canonical path to the VoiceVessel launcher
        self.launcher_path = "C:/Users/Wykeve/Projects/VoiceVessel/Invoke-VoiceVessel.ps1"
        self.active_persona = "echo" # Default
        self.default_engine = "sapi5" # Fast

    def speak(self, text: str, persona: Optional[str] = None, engine: Optional[str] = None) -> bool:
        """
        Invokes the VoiceVessel launcher to speak the given text.
        
        Args:
            text: The message to speak.
            persona: Optional persona (Ryuzu, Roland, Sonmi, etc.)
            engine: Optional engine (sapi5, chatterbox, elevenlabs)
        """
        p = persona or self.active_persona
        e = engine or self.default_engine
        
        logger.info(f"Speaking via {e} (Persona: {p}): {text[:50]}...")
        
        try:
            # We use PowerShell to call the launcher
            cmd = [
                "powershell.exe",
                "-ExecutionPolicy", "Bypass",
                "-File", self.launcher_path,
                "-Text", text,
                "-Engine", e,
                "-Persona", p
            ]
            
            # Non-blocking for speed, but we could wait if needed
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception as e:
            logger.error(f"Voice execution failed: {e}")
            return False

    def set_persona(self, persona: str):
        """Sets the default persona for the voice."""
        self.active_persona = persona
        logger.info(f"Voice persona set to: {persona}")

def get_voice_adapter() -> VoiceAdapter:
    """Returns a singleton-like instance of the VoiceAdapter."""
    return VoiceAdapter()
