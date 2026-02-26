---
name: voidcat-conventions
description: >
  Load before writing or editing any Python code in Sovereign Spirit.
  Teaches the exact patterns required by VoidCat coding standards to
  prevent the class of issues found in the 2026-02-26 audit.
user-invocable: false
---

# VoidCat Sovereign Spirit — Coding Conventions

Apply these patterns in all code you write or edit for this project.

## Database Access

The `DatabaseClient` uses SQLAlchemy AsyncSession. Never use `db.pool`.

**Correct pattern:**
```python
async with db.session() as session:
    result = await session.execute(
        text("SELECT id, content FROM messages WHERE agent_id = :agent_id"),
        {"agent_id": agent_id}
    )
    rows = result.mappings().all()
```

**Wrong:**
```python
async with db.pool.acquire() as conn:   # db.pool does not exist
    rows = await conn.fetch(query, *params)
```

## Datetime — Law of Time

Always timezone-aware. No exceptions.

```python
from datetime import datetime, timezone

# Correct
now = datetime.now(timezone.utc)

# Wrong — both are forbidden
datetime.now()        # naked
datetime.utcnow()     # deprecated in Python 3.12+
```

For SQLAlchemy column defaults:
```python
timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
```

## Logging — No print()

```python
import logging
logger = logging.getLogger("sovereign.module_name")

# Correct
logger.info("Agent started")
logger.warning(f"Fluid Persona evaluation failed: {e}")
logger.error(f"Database write failed: {e}")

# Wrong — violates VOID-DIR-004
print(f"Something happened: {e}")
```

## Type Hints — Everything

All function signatures require full type hints.

```python
from typing import Optional, List, Dict, Any

async def get_agent_state(
    agent_id: str,
    include_traits: bool = False,
) -> Optional[AgentState]:
    ...
```

## Secrets — Never Hardcoded

```python
# Correct
api_key = os.getenv("OPENAI_API_KEY")

# Wrong — will be caught by secret_guard hook and blocked
api_key = "sk-proj-abc123..."
```

In YAML config files, use: `api_key: "${OPENAI_API_KEY}"`

## Async — Never Block the Event Loop

```python
import asyncio

# Correct — run blocking operations in a thread
result = await asyncio.to_thread(blocking_function, arg1, arg2)

# Wrong — blocks the entire event loop
result = blocking_function(arg1, arg2)
```

## Module-Level Imports Only

```python
# Correct — all imports at the top of the file
import asyncio
import json
from datetime import datetime, timezone

# Wrong — late import inside a function
async def my_handler():
    import asyncio  # Don't do this
```

## Singletons — Use Module-Level Variables

```python
_manager: Optional[ConnectionManager] = None

def get_connection_manager() -> ConnectionManager:
    global _manager
    if _manager is None:
        _manager = ConnectionManager()
    return _manager
```

## Commit Prefixes (VOID-DIR-004)

`feat:` `fix:` `docs:` `refactor:` `chore:`

## File Naming

- Python files: `snake_case.py`
- Web assets: `kebab-case.js`
