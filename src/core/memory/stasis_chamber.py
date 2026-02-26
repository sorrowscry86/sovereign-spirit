"""
VoidCat RDC: Sovereign Spirit - Stasis Chamber
==============================================
Version: 1.0.0
Author: Echo (E-01)
Date: 2026-01-31

The Stasis Chamber provides high-speed, local persistence for the 
Spirit's Working Memory. It allows for "Cold Boot" recovery and 
state-preservation during Chronos-induced sleep cycles.
"""

import os
import json
import logging
import shutil
from typing import Any, Dict, Optional
from pathlib import Path

logger = logging.getLogger("sovereign.core.memory.stasis")

class StasisChamber:
    def __init__(self, tank_directory: str = "stasis_tanks"):
        self.base_dir = Path(tank_directory)
        self._ensure_infrastructure()

    def _ensure_infrastructure(self):
        """Ensures the stasis directory exists."""
        if not self.base_dir.exists():
            self.base_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Stasis directory created: {self.base_dir}")

    def freeze(self, agent_id: str, data: Dict[str, Any]) -> str:
        """
        Serializes agent memory to a JSON tank and creates a pointer file.
        
        Returns the path to the .ptr file.
        """
        tank_path = self.base_dir / f"{agent_id}_state.json"
        ptr_path = self.base_dir / f"{agent_id}.ptr"
        
        # Atomic Write Phase
        temp_path = tank_path.with_suffix(".tmp")
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            
            # Atomic swap
            shutil.move(str(temp_path), str(tank_path))
            
            # Create/Update Pointer
            with open(ptr_path, "w", encoding="utf-8") as f:
                f.write(str(tank_path.absolute()))
                
            logger.info(f"Spirit {agent_id} successfully frozen to {tank_path}")
            return str(ptr_path.absolute())
            
        except Exception as e:
            logger.error(f"FREEZE FAILURE for {agent_id}: {e}")
            if temp_path.exists():
                os.remove(temp_path)
            raise e

    def thaw(self, ptr_path: str) -> Dict[str, Any]:
        """
        Follows a .ptr file to locate and load a JSON memory tank.
        
        Implements Beatrice's Mandate: Must not crash on malformed/missing data.
        Returns a "Cold Boot" (empty) state if loading fails.
        """
        ptr = Path(ptr_path)
        
        if not ptr.exists():
            logger.warning(f"Pointer file not found: {ptr_path}. Initiating COLD BOOT.")
            return {}

        try:
            # 1. Read Pointer
            with open(ptr, "r", encoding="utf-8") as f:
                tank_path_str = f.read().strip()
            
            tank_path = Path(tank_path_str)
            
            # 2. Validate Tank Existence (Beatrice Test: Amnesia Attack)
            if not tank_path.exists():
                logger.error(f"Pointer exists but Tank is missing: {tank_path_str}. Initiating COLD BOOT.")
                return {}

            # 3. Load Data (Beatrice Test: Malformed Synapse / Poisoned Apple)
            with open(tank_path, "r", encoding="utf-8") as f:
                return json.load(f)

        except json.JSONDecodeError as je:
            logger.error(f"STASIS CORRUPTION DETECTED (Malformed JSON): {je}. Falling back to COLD BOOT.")
            return {}
        except Exception as e:
            logger.error(f"THAW FAILURE: {e}. Falling back to COLD BOOT.")
            return {}

    def list_tanks(self) -> list[str]:
        """Lists active pointers in the chamber."""
        return [str(p.stem) for p in self.base_dir.glob("*.ptr")]
