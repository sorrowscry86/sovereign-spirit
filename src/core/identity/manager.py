"""
VoidCat RDC: Sovereign Spirit Core - Identity Manager
=====================================================
Pillar 3: Soul-Body Decoupling
Implementation of the Spirit Sync Protocol (VSSP).
"""

import logging
import json
from typing import Optional, Dict, Any

from src.core.database import DatabaseClient, AgentState
from src.core.inference.prompts import build_system_prompt

logger = logging.getLogger("sovereign.identity.manager")

class IdentityManager:
    """
    Manages the dynamic switching of agent identities (Spirit Sync).
    Allows an agent body to 'channel' a target spirit's DNA.
    """
    
    def __init__(self, db: DatabaseClient):
        self.db = db

    async def sync_agent_identity(self, agent_id: str, target_spirit_name: str) -> Optional[AgentState]:
        """
        Syncs an agent's active profile with a spirit from the Pantheon.
        
        Args:
            agent_id: The ID of the agent body (e.g., 'vessel_01').
            target_spirit_name: The name of the spirit to sync with (e.g., 'Albedo').
            
        Returns:
            The updated AgentState if successful.
        """
        logger.info(f"Initiating Spirit Sync: {agent_id} -> {target_spirit_name}")
        
        # 1. Fetch the target spirit's DNA from the database
        spirit_dna = await self.db.get_agent_state(target_spirit_name)
        if not spirit_dna:
            logger.error(f"Sync failed: Spirit '{target_spirit_name}' not found in Pantheon.")
            return None
            
        # 2. Extract traits and metadata
        traits = spirit_dna.traits
        archetype = traits.get("archetype", "Unknown")
        
        # 3. Generate the specialized system prompt
        specialized_prompt = build_system_prompt(
            agent_name=spirit_dna.name,
            designation=spirit_dna.designation,
            archetype=archetype,
            traits={
                "big_five": traits.get("big_five", {}),
                "expertise_tags": spirit_dna.expertise_tags,
                "behavior_modes": spirit_dna.behavior_modes
            }
        )
        
        # 4. Apply the sync to the agent body in the database
        # Note: In a real 'Body-Soul' decouple, we update the active state of the agent_id.
        # For now, we update the system_prompt of the agent_id to match the spirit's DNA.
        async with self.db.session() as session:
            try:
                from sqlalchemy import text
                await session.execute(
                    text("""
                        UPDATE agents
                        SET designation = :designation,
                            system_prompt_template = :prompt,
                            traits_json = :traits,
                            behavior_modes = :modes,
                            expertise_tags = :expertise,
                            current_mood = 'Synchronized'
                        WHERE LOWER(name) = LOWER(:agent_id)
                    """),
                    {
                        "agent_id": agent_id,
                        "designation": spirit_dna.designation,
                        "prompt": specialized_prompt,
                        "traits": spirit_dna.traits,  # This is already a dict
                        "modes": spirit_dna.behavior_modes,
                        "expertise": spirit_dna.expertise_tags
                    }
                )
                await session.commit()
                logger.info(f"Spirit Sync Complete: {agent_id} is now manifesting {target_spirit_name}.")
                return await self.db.get_agent_state(agent_id)
            except Exception as e:
                await session.rollback()
                logger.error(f"Spirit Sync failed for {agent_id} -> {target_spirit_name}: {e}")
                raise

_manager: Optional[IdentityManager] = None

def get_identity_manager(db: DatabaseClient) -> IdentityManager:
    """Get or create the singleton identity manager."""
    global _manager
    if _manager is None:
        _manager = IdentityManager(db)
    return _manager
