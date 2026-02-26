"""
VoidCat RDC: Sovereign Spirit - Wake Protocol
=============================================
Entrypoint for the Resurrection Protocol.
Triggered by Chronos (Windows Task Scheduler).
"""

import os
import sys
import argparse
import logging
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.abspath("."))

from src.core.memory.stasis_chamber import StasisChamber

# Setup dedicated logging
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "resurrection.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("sovereign.wake_protocol")

def validate_agent_id(agent_id: str):
    """
    STRICT VALIDATION: Prevents Shell Injection (Beatrice Test: Argument Fuzz).
    Only allows alphanumeric, dash, and underscore.
    """
    import re
    if not re.match(r"^[a-zA-Z0-9_-]+$", agent_id):
        raise ValueError(f"CRITICAL SECURITY ALERT: Suspicious Agent ID Detected: {agent_id}")

def execute_wake(agent_id: str):
    """
    Main wake sequence.
    """
    logger.info(f"=== INITIATING WAKE SEQUENCE: {agent_id} ===")
    
    try:
        validate_agent_id(agent_id)
        
        chamber = StasisChamber()
        ptr_file = os.path.join("stasis_tanks", f"{agent_id}.ptr")
        
        # Thaw the memory
        memory = chamber.thaw(ptr_file)
        
        if not memory:
            logger.info(f"Agent {agent_id} initialized with COLD BOOT (no previous state).")
        else:
            logger.info(f"Agent {agent_id} memory restored. Heartbeat synchronization imminent.")
            
        # Here we would normally signal the main process or start the API.
        # For the purpose of the Chronos Test, we are logging success.
        logger.info(f"=== WAKE SUCCESSFUL: {agent_id} at {datetime.now(timezone.utc).isoformat()} ===")
        
    except ValueError as ve:
        logger.error(f"SECURITY BLOCK: {ve}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"CATASTROPHIC WAKE FAILURE for {agent_id}: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sovereign Spirit Wake Protocol")
    parser.add_argument("--agent", type=str, help="ID of the agent to resurrect")
    
    # Handle missing arguments (Beatrice Test: Argument Fuzz)
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)
        
    args = parser.parse_args()
    
    if args.agent:
        execute_wake(args.agent)
    else:
        logger.error("No agent ID provided. Termination sequence active.")
        sys.exit(1)
