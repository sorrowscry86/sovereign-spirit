"""
VoidCat RDC: Sovereign Spirit — Ryuzu Agent Merge Script
=========================================================
One-time migration to merge duplicate "Ryuzu Meyer" rows into the
canonical "Ryuzu" agent in the PostgreSQL agents table.

Reassigns all foreign keys (tether_messages, tether_participants,
projects, memory_events, heartbeat_logs, agent_messages) then deletes
the duplicate row.

Usage:
    python scripts/merge_ryuzu.py
"""

import asyncio
import logging
import sys
from pathlib import Path

# Ensure project root is on sys.path so `src.*` imports resolve
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from src.core.database import get_database

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("merge_ryuzu")


async def merge() -> None:
    db = get_database()
    await db.initialize()

    async with db.session() as session:
        # ------------------------------------------------------------------
        # 1. Find all rows matching "ryuzu" (case-insensitive)
        # ------------------------------------------------------------------
        result = await session.execute(
            text(
                "SELECT id, name, designation, traits_json FROM agents WHERE name ILIKE :pattern"
            ),
            {"pattern": "%ryuzu%"},
        )
        rows = result.fetchall()

        if not rows:
            logger.info("No rows matching '%%ryuzu%%' found. Nothing to do.")
            return

        logger.info("Found %d agent row(s) matching 'ryuzu':", len(rows))
        for row in rows:
            logger.info(
                "  id=%s  name=%s  designation=%s", row.id, row.name, row.designation
            )

        # ------------------------------------------------------------------
        # 2. Identify canonical vs duplicate(s)
        # ------------------------------------------------------------------
        canonical = None
        duplicates = []
        for row in rows:
            if row.name == "Ryuzu":
                canonical = row
            else:
                duplicates.append(row)

        if canonical is None:
            logger.error(
                "No canonical 'Ryuzu' row found — only duplicates: %s. Aborting.",
                [r.name for r in duplicates],
            )
            return

        if not duplicates:
            logger.info(
                "Only the canonical 'Ryuzu' row exists. No duplicates to merge."
            )
            return

        for dup in duplicates:
            logger.info(
                "Merging duplicate '%s' (id=%s) into canonical 'Ryuzu' (id=%s)",
                dup.name,
                dup.id,
                canonical.id,
            )

            # --------------------------------------------------------------
            # 3. Copy designation if canonical's is empty
            # --------------------------------------------------------------
            if (
                not canonical.designation or canonical.designation.strip() == ""
            ) and dup.designation:
                logger.info(
                    "  Copying designation '%s' from duplicate.", dup.designation
                )
                await session.execute(
                    text("UPDATE agents SET designation = :desig WHERE id = :cid"),
                    {"desig": dup.designation, "cid": canonical.id},
                )

            # --------------------------------------------------------------
            # 4. Merge unique traits from duplicate into canonical
            # --------------------------------------------------------------
            canonical_traits: dict = (
                canonical.traits_json if isinstance(canonical.traits_json, dict) else {}
            )
            dup_traits: dict = (
                dup.traits_json if isinstance(dup.traits_json, dict) else {}
            )

            if dup_traits:
                merged_traits = {
                    **dup_traits,
                    **canonical_traits,
                }  # canonical wins on conflicts
                if merged_traits != canonical_traits:
                    logger.info(
                        "  Merging traits: %d keys from duplicate, %d from canonical → %d merged.",
                        len(dup_traits),
                        len(canonical_traits),
                        len(merged_traits),
                    )
                    await session.execute(
                        text(
                            "UPDATE agents SET traits_json = :traits::jsonb WHERE id = :cid"
                        ),
                        {
                            "traits": __import__("json").dumps(merged_traits),
                            "cid": canonical.id,
                        },
                    )

            # --------------------------------------------------------------
            # 5. Reassign foreign keys from duplicate → canonical
            # --------------------------------------------------------------

            # 5a. tether_messages.sender_agent_id
            res = await session.execute(
                text(
                    "UPDATE tether_messages SET sender_agent_id = :cid WHERE sender_agent_id = :did"
                ),
                {"cid": canonical.id, "did": dup.id},
            )
            logger.info(
                "  tether_messages.sender_agent_id: %d rows updated.", res.rowcount
            )

            # 5b. tether_messages.recipient_agent_id
            res = await session.execute(
                text(
                    "UPDATE tether_messages SET recipient_agent_id = :cid WHERE recipient_agent_id = :did"
                ),
                {"cid": canonical.id, "did": dup.id},
            )
            logger.info(
                "  tether_messages.recipient_agent_id: %d rows updated.", res.rowcount
            )

            # 5c. tether_participants.agent_id (composite PK: thread_id + agent_id)
            #     Delete duplicate participation where canonical is already in the same thread,
            #     then update remaining rows.
            res = await session.execute(
                text("""
                    DELETE FROM tether_participants
                    WHERE agent_id = :did
                      AND thread_id IN (
                          SELECT thread_id FROM tether_participants WHERE agent_id = :cid
                      )
                """),
                {"did": dup.id, "cid": canonical.id},
            )
            logger.info(
                "  tether_participants: %d duplicate participations deleted (canonical already present).",
                res.rowcount,
            )

            res = await session.execute(
                text(
                    "UPDATE tether_participants SET agent_id = :cid WHERE agent_id = :did"
                ),
                {"cid": canonical.id, "did": dup.id},
            )
            logger.info(
                "  tether_participants: %d rows reassigned to canonical.", res.rowcount
            )

            # 5d. projects.lead_agent_id (TEXT column — stores agent name, not UUID)
            res = await session.execute(
                text(
                    "UPDATE projects SET lead_agent_id = :cname WHERE lead_agent_id = :dname"
                ),
                {"cname": "Ryuzu", "dname": dup.name},
            )
            logger.info(
                "  projects.lead_agent_id: %d rows updated ('%s' → 'Ryuzu').",
                res.rowcount,
                dup.name,
            )

            # 5e. memory_events.author_id
            res = await session.execute(
                text(
                    "UPDATE memory_events SET author_id = :cid WHERE author_id = :did"
                ),
                {"cid": canonical.id, "did": dup.id},
            )
            logger.info("  memory_events.author_id: %d rows updated.", res.rowcount)

            # 5f. heartbeat_logs.agent_id
            res = await session.execute(
                text("UPDATE heartbeat_logs SET agent_id = :cid WHERE agent_id = :did"),
                {"cid": canonical.id, "did": dup.id},
            )
            logger.info("  heartbeat_logs.agent_id: %d rows updated.", res.rowcount)

            # 5g. agent_messages.from_agent_id / to_agent_id
            res = await session.execute(
                text(
                    "UPDATE agent_messages SET from_agent_id = :cid WHERE from_agent_id = :did"
                ),
                {"cid": canonical.id, "did": dup.id},
            )
            logger.info(
                "  agent_messages.from_agent_id: %d rows updated.", res.rowcount
            )

            res = await session.execute(
                text(
                    "UPDATE agent_messages SET to_agent_id = :cid WHERE to_agent_id = :did"
                ),
                {"cid": canonical.id, "did": dup.id},
            )
            logger.info("  agent_messages.to_agent_id: %d rows updated.", res.rowcount)

            # --------------------------------------------------------------
            # 6. Delete the duplicate row
            # --------------------------------------------------------------
            await session.execute(
                text("DELETE FROM agents WHERE id = :did"),
                {"did": dup.id},
            )
            logger.info("  Deleted duplicate agent '%s' (id=%s).", dup.name, dup.id)

        # ------------------------------------------------------------------
        # 7. Commit the transaction
        # ------------------------------------------------------------------
        await session.commit()
        logger.info("Transaction committed. Merge complete.")


def main() -> None:
    asyncio.run(merge())


if __name__ == "__main__":
    main()
