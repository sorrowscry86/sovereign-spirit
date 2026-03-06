"""
VoidCat RDC: Tether Protocol — Data Migration Script
=====================================================
Migrates existing messages and agent_messages data into the
unified tether_threads / tether_messages schema.

Run once after deploying 02_tether_schema.sql.

Usage:
    python scripts/migrate_to_tether.py

Requires DATABASE_URL environment variable or defaults to Docker internal.
"""

import asyncio
import logging
import os
import re
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("tether_migration")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://voidcat:sovereign_spirit@localhost:5432/voidcat_rdc",
)


async def migrate() -> None:
    """Run the full migration."""
    engine = create_async_engine(DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with session_factory() as session:
        # =====================================================================
        # Step 1: Build agent name → UUID lookup
        # =====================================================================
        result = await session.execute(text("SELECT id, name FROM agents"))
        agents = {row.name.lower(): str(row.id) for row in result.fetchall()}
        logger.info(f"Found {len(agents)} agents: {list(agents.keys())}")

        # =====================================================================
        # Step 2: Migrate `messages` table (user-agent conversations)
        # =====================================================================
        result = await session.execute(
            text(
                "SELECT id, sender, content, timestamp, agent_id FROM messages ORDER BY timestamp ASC"
            )
        )
        messages_rows = result.fetchall()
        logger.info(f"Migrating {len(messages_rows)} rows from messages table...")

        # Group messages by agent_id into threads
        agent_threads: dict[str, str] = {}  # agent_id → thread_id

        for row in messages_rows:
            agent_id = row.agent_id.lower() if row.agent_id else ""
            agent_uuid = agents.get(agent_id)

            if agent_id not in agent_threads:
                # Create a thread for this user-agent conversation
                thread_result = await session.execute(
                    text("""
                        INSERT INTO tether_threads (thread_type, created_by, subject, created_at)
                        VALUES ('user_agent', :created_by, :subject, :created_at)
                        RETURNING id
                    """),
                    {
                        "created_by": "migration",
                        "subject": f"Migrated: Conversation with {agent_id}",
                        "created_at": row.timestamp or datetime.now(timezone.utc),
                    },
                )
                thread_row = thread_result.fetchone()
                thread_id = str(thread_row.id)
                agent_threads[agent_id] = thread_id

                # Add agent as participant
                if agent_uuid:
                    await session.execute(
                        text("""
                            INSERT INTO tether_participants (thread_id, agent_id)
                            VALUES (:thread_id, :agent_id)
                            ON CONFLICT DO NOTHING
                        """),
                        {"thread_id": thread_id, "agent_id": agent_uuid},
                    )

            thread_id = agent_threads[agent_id]
            sender_type = "user" if row.sender == "user" else "agent"
            sender_name = "User" if row.sender == "user" else agent_id.title()

            await session.execute(
                text("""
                    INSERT INTO tether_messages
                        (thread_id, sender_type, sender_name, sender_agent_id,
                         recipient_agent_id, content, message_type, status, created_at)
                    VALUES
                        (:thread_id, :sender_type, :sender_name, :sender_agent_id,
                         :recipient_agent_id, :content, 'chat', 'read', :created_at)
                """),
                {
                    "thread_id": thread_id,
                    "sender_type": sender_type,
                    "sender_name": sender_name,
                    "sender_agent_id": agent_uuid if sender_type == "agent" else None,
                    "recipient_agent_id": agent_uuid if sender_type == "user" else None,
                    "content": row.content,
                    "created_at": row.timestamp or datetime.now(timezone.utc),
                },
            )

        logger.info(
            f"Migrated {len(messages_rows)} messages into {len(agent_threads)} threads"
        )

        # =====================================================================
        # Step 3: Migrate `agent_messages` table
        # =====================================================================
        result = await session.execute(text("""
                SELECT id, from_agent_id, to_agent_id, content, status, created_at
                FROM agent_messages
                ORDER BY created_at ASC
            """))
        agent_msg_rows = result.fetchall()
        logger.info(
            f"Migrating {len(agent_msg_rows)} rows from agent_messages table..."
        )

        # Reverse lookup: UUID → name
        uuid_to_name = {v: k for k, v in agents.items()}

        socialize_pattern = re.compile(r"^\[To (\w+)\]: (.+)$", re.DOTALL)
        migrated_count = 0

        for row in agent_msg_rows:
            from_uuid = str(row.from_agent_id) if row.from_agent_id else None
            to_uuid = str(row.to_agent_id) if row.to_agent_id else None
            content = row.content

            # Parse SOCIALIZE content format: "[To AgentName]: message"
            socialize_match = socialize_pattern.match(content)
            if socialize_match and from_uuid:
                target_name = socialize_match.group(1).lower()
                actual_content = socialize_match.group(2)
                resolved_to_uuid = agents.get(target_name)
                if resolved_to_uuid:
                    to_uuid = resolved_to_uuid
                    content = actual_content

            # Determine sender info
            sender_type = "agent" if from_uuid else "user"
            sender_name = (
                uuid_to_name.get(from_uuid, "Unknown").title() if from_uuid else "User"
            )

            # Create or find thread
            pair_key = f"{from_uuid or 'user'}:{to_uuid or 'broadcast'}"
            if pair_key not in agent_threads:
                thread_type = "agent_agent" if from_uuid and to_uuid else "user_agent"
                thread_result = await session.execute(
                    text("""
                        INSERT INTO tether_threads (thread_type, created_by, subject, created_at)
                        VALUES (:thread_type, :created_by, :subject, :created_at)
                        RETURNING id
                    """),
                    {
                        "thread_type": thread_type,
                        "created_by": sender_name,
                        "subject": f"Migrated: {pair_key}",
                        "created_at": row.created_at or datetime.now(timezone.utc),
                    },
                )
                thread_row = thread_result.fetchone()
                thread_id = str(thread_row.id)
                agent_threads[pair_key] = thread_id

                # Add participants
                if from_uuid:
                    await session.execute(
                        text("""
                            INSERT INTO tether_participants (thread_id, agent_id)
                            VALUES (:thread_id, :agent_id)
                            ON CONFLICT DO NOTHING
                        """),
                        {"thread_id": thread_id, "agent_id": from_uuid},
                    )
                if to_uuid:
                    await session.execute(
                        text("""
                            INSERT INTO tether_participants (thread_id, agent_id)
                            VALUES (:thread_id, :agent_id)
                            ON CONFLICT DO NOTHING
                        """),
                        {"thread_id": thread_id, "agent_id": to_uuid},
                    )

            thread_id = agent_threads[pair_key]

            # Map old status to new
            status_map = {
                "pending": "pending",
                "received": "pending",
                "delivered": "delivered",
                "processed": "read",
                "read": "read",
                "expired": "expired",
            }
            new_status = status_map.get(row.status, "read")

            await session.execute(
                text("""
                    INSERT INTO tether_messages
                        (thread_id, sender_type, sender_name, sender_agent_id,
                         recipient_agent_id, content, message_type, status, created_at)
                    VALUES
                        (:thread_id, :sender_type, :sender_name, :sender_agent_id,
                         :recipient_agent_id, :content, :message_type, :status, :created_at)
                """),
                {
                    "thread_id": thread_id,
                    "sender_type": sender_type,
                    "sender_name": sender_name,
                    "sender_agent_id": from_uuid,
                    "recipient_agent_id": to_uuid,
                    "content": content,
                    "message_type": "ponder_social" if socialize_match else "chat",
                    "status": new_status,
                    "created_at": row.created_at or datetime.now(timezone.utc),
                },
            )
            migrated_count += 1

        await session.commit()
        logger.info(f"Migrated {migrated_count} agent_messages rows")

    # =====================================================================
    # Step 4: Rename legacy tables (optional — uncomment when ready)
    # =====================================================================
    # async with session_factory() as session:
    #     await session.execute(text("ALTER TABLE messages RENAME TO messages_v1_retired"))
    #     await session.execute(text("ALTER TABLE agent_messages RENAME TO agent_messages_v1_retired"))
    #     await session.commit()
    #     logger.info("Legacy tables renamed to *_v1_retired")

    await engine.dispose()
    logger.info("Migration complete.")


if __name__ == "__main__":
    asyncio.run(migrate())
