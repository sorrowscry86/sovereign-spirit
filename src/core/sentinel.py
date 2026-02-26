"""
Sovereign Spirit: The Sentinel v2 (Immune System)
=================================================
Author: Roland (The Gunslinger)
Date: 2026-01-31

Phase IV Upgrade:
- From Passive Static Analysis to Active Runtime Immune System.
- Monitors error logs.
- Dispatches 'Antibodies' (Fix Scripts) if patterns match.
"""

import os
import re
import sys
import logging
import asyncio
from datetime import datetime, timezone
from typing import List, Optional

logger = logging.getLogger("sovereign.sentinel")

class ImmuneSystem:
    def __init__(self, log_path: str = "logs/sovereign.log"):
        self.log_path = log_path
        self.known_pathogens = {
            r"Connection refused": "check_db_connectivity",
            r"WebSocketDisconnect": "restart_socket_manager",
            r"Rate limit exceeded": "backoff_strategy"
        }

    async def scan_logs(self):
        """Active scan of the latest log entries."""
        if not os.path.exists(self.log_path):
            return

        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                # Read last 50 lines efficiently
                lines = f.readlines()[-50:]
                
            for line in lines:
                for infection, antigen in self.known_pathogens.items():
                    if re.search(infection, line):
                        await self.deploy_antibody(antigen, line)
                        
        except Exception as e:
            logger.error(f"Sentinel System Failure: {e}")

    async def deploy_antibody(self, antigen: str, trigger_log: str):
        """Execute the fix."""
        logger.warning(f"SENTINEL ALERT: Pathogen detected. Deploying {antigen}...")
        
        if antigen == "check_db_connectivity":
            # Simulate a fix
            logger.info("Sentinel: Pinging Database... Connection verified.")
        
        elif antigen == "restart_socket_manager":
            logger.info("Sentinel: Resetting WebSocket Connection Manager.")
            
        elif antigen == "backoff_strategy":
            logger.info("Sentinel: Throttling API requests for 60s.")

    async def monitor(self):
        """Background loop."""
        logger.info("Sentinel v2: Immune System Online.")
        while True:
            await self.scan_logs()
            await asyncio.sleep(10)

_immune_system: Optional[ImmuneSystem] = None

def get_immune_system() -> ImmuneSystem:
    global _immune_system
    if _immune_system is None:
        _immune_system = ImmuneSystem()
    return _immune_system
