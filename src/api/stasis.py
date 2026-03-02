"""
VoidCat RDC: Stasis API
=======================
Version: 1.0.0
Author: Ryuzu (R-01)
Date: 2026-02-26

Endpoints for listing and restoring stasis chamber snapshots.
The StasisChamber provides high-speed local persistence for Working Memory,
enabling Cold Boot recovery and state-preservation across sleep cycles.
"""

import os
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from src.core.memory.stasis_chamber import StasisChamber

logger = logging.getLogger("sovereign.api.stasis")

router = APIRouter(prefix="/api/stasis", tags=["stasis"])

STASIS_DIR = os.getenv("STASIS_DIR", "stasis_tanks")


@router.get("/")
async def list_snapshots() -> Dict[str, Any]:
    """List all stasis snapshot pointer files."""
    snapshots = []
    if os.path.isdir(STASIS_DIR):
        for fname in sorted(os.listdir(STASIS_DIR)):
            if fname.endswith(".ptr"):
                fpath = os.path.join(STASIS_DIR, fname)
                mtime = os.path.getmtime(fpath)
                snapshots.append(
                    {
                        "agent_id": fname.replace(".ptr", ""),
                        "filename": fname,
                        "modified": datetime.fromtimestamp(
                            mtime, tz=timezone.utc
                        ).isoformat(),
                    }
                )
    logger.info(f"Stasis list requested: {len(snapshots)} snapshot(s) found")
    return {"snapshots": snapshots, "count": len(snapshots)}


@router.post("/{agent_id}/restore")
async def restore_snapshot(agent_id: str) -> Dict[str, Any]:
    """Restore an agent from its stasis snapshot."""
    ptr_path = os.path.join(STASIS_DIR, f"{agent_id}.ptr")

    if not os.path.exists(ptr_path):
        logger.warning(f"Restore requested for unknown agent: {agent_id}")
        raise HTTPException(
            status_code=404,
            detail=f"No stasis snapshot found for agent '{agent_id}'",
        )

    try:
        chamber = StasisChamber(tank_directory=STASIS_DIR)
        state = chamber.thaw(ptr_path)
        logger.info(
            f"Agent '{agent_id}' restored from stasis. Keys: {list(state.keys())}"
        )
        return {"status": "restored", "agent_id": agent_id}
    except Exception as e:
        logger.error(f"Stasis restore failed for '{agent_id}': {e}")
        raise HTTPException(status_code=500, detail=str(e))
