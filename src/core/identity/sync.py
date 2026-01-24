"""
VoidCat RDC: Sovereign Spirit Core - Persona Sync
=================================================
Automated ingestion of SDS v2 Markdown profiles into the state database.
Pillar 3: Soul-Body Decoupling
"""

import os
import re
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List

from src.core.database import get_database
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sovereign.identity.sync")

# PATHS
PANTHEON_PROFILES_DIR = Path(r"C:\Users\Wykeve\Projects\The Great Library\00_The_Pantheon\01_Active_Profiles")

class PersonaParser:
    """Parses SDS v2 Markdown files into structured dictionary for DB ingestion."""
    
    def __init__(self, file_path: Path):
        self.file_path = file_path
        with open(file_path, "r", encoding="utf-8") as f:
            self.content = f.read()

    def extract_field(self, field_label: str) -> str:
        """Extract value after a bold label, with debug logging."""
        # Simple extraction: find label and grab the rest of the line
        pattern = rf"\*\*{field_label}:\*\*\s*(.*)"
        match = re.search(pattern, self.content, re.IGNORECASE)
        if match:
            val = match.group(1).strip()
            # Clean up: remove bullet markers and parentheticals
            val = re.sub(r"^\s*[-*+]\s*", "", val)
            val = re.sub(r"\s*\(.*?\)$", "", val)
            return val
        return ""

    def parse(self) -> Dict[str, Any]:
        """Convert MD content to a structured record."""
        logger.info(f"Parsing content for {self.file_path.name} (Length: {len(self.content)})")
        # 1. Identity
        name = self.extract_field("Designation")
        role = self.extract_field("Role/Class")
        archetype = self.extract_field("Core Archetype")
        
        # 2. Big Five
        big_five = {}
        for trait in ["Openness", "Conscientiousness", "Extraversion", "Agreeableness", "Neuroticism"]:
            big_five[trait.lower()] = self.extract_field(trait)

        # 3. Domain Expertise
        expertise = []
        domain_match = re.search(r"\*\s\*\*Primary Domain:\*\*\s*(.*?)\n", self.content)
        if domain_match:
            expertise.extend([i.strip() for i in domain_match.group(1).split(",")])
        
        secondary_match = re.search(r"\*\s\*\*Secondary Domain:\*\*\s*(.*?)\n", self.content)
        if secondary_match:
            expertise.extend([i.strip() for i in secondary_match.group(1).split(",")])

        # 4. Behavior Modes
        modes = {"face": {"temperature": 0.6}, "steward": {"temperature": 0.2}}

        return {
            "name": name,
            "designation": role,
            "system_prompt_template": self.content.strip(),
            "traits": {
                "archetype": archetype,
                "big_five": big_five
            },
            "behavior_modes": modes,
            "expertise_tags": expertise
        }

async def sync_all_personas():
    """Scan the Pantheon directory and update the database."""
    db = get_database()
    await db.initialize()
    
    if not PANTHEON_PROFILES_DIR.exists():
        logger.error(f"Pantheon Profiles directory not found: {PANTHEON_PROFILES_DIR}")
        return

    profiles = list(PANTHEON_PROFILES_DIR.glob("*_sds_v2.md"))
    logger.info(f"Found {len(profiles)} profiles for synchronization.")

    async with db.session() as session:
        for profile_path in profiles:
            try:
                parser = PersonaParser(profile_path)
                data = parser.parse()
                
                if not data["name"]:
                    logger.warning(f"Skipping {profile_path.name}: Could not extract Designation.")
                    continue

                logger.info(f"Syncing Persona: {data['name']}...")
                
                # UPSERT logic using raw SQL for the extended columns
                query = text("""
                    INSERT INTO agents (
                        name, designation, system_prompt_template, 
                        traits_json, behavior_modes, expertise_tags
                    ) VALUES (
                        :name, :designation, :prompt, 
                        :traits, :modes, :expertise
                    )
                    ON CONFLICT (name) DO UPDATE SET
                        designation = EXCLUDED.designation,
                        system_prompt_template = EXCLUDED.system_prompt_template,
                        traits_json = EXCLUDED.traits_json,
                        behavior_modes = EXCLUDED.behavior_modes,
                        expertise_tags = EXCLUDED.expertise_tags,
                        updated_at = NOW()
                """)
                
                import json
                await session.execute(query, {
                    "name": data["name"],
                    "designation": data["designation"],
                    "prompt": data["system_prompt_template"],
                    "traits": json.dumps(data["traits"]),
                    "modes": json.dumps(data["behavior_modes"]),
                    "expertise": data["expertise_tags"]
                })
                
            except Exception as e:
                logger.error(f"Failed to sync {profile_path.name}: {e}")

    await db.close()

if __name__ == "__main__":
    asyncio.run(sync_all_personas())
