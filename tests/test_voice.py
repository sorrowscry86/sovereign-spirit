"""
Test: Voice Integration
=======================
Verifies that the Sovereign Spirit can invoke the VoiceVessel.
"""
import asyncio
import logging
from src.adapters.voice_adapter import VoiceAdapter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_voice")

async def test_voice():
    logger.info("Initializing Voice Adapter...")
    voice = VoiceAdapter()
    
    logger.info("Testing SAPI5 (Fast) Voice...")
    success = voice.speak("System check. Voice integration initialized. Ready for Phase Four.", persona="echo", engine="sapi5")
    
    if success:
        logger.info("[PASS] Voice command dispatched.")
    else:
        logger.error("[FAIL] Voice command failed.")

if __name__ == "__main__":
    asyncio.run(test_voice())
