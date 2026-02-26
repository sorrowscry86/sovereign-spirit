"""
VoidCat RDC: Sovereign Spirit Core - Cache Client (Redis)
=========================================================
Async Redis wrapper for working memory and event bus.
"""

import os
import logging
from typing import Optional
import redis.asyncio as redis

logger = logging.getLogger("sovereign.cache")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
# Docker default is redis://redis:6379, Host default is localhost


class CacheClient:
    """Async Redis client wrapper."""

    def __init__(self, url: str = REDIS_URL):
        self._url = url
        self._redis: Optional[redis.Redis] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize Redis connection pool."""
        try:
            # Auto-detect docker vs host mapping if generic hostname fails?
            # redis-py handles connection lazily usually, but we want to ping.

            self._redis = redis.from_url(self._url, socket_timeout=2.0)
            await self._redis.ping()
            self._initialized = True
            logger.info(f"Connected to Redis at {self._url}")

        except Exception as e:
            # Fallback logic for localhost if 'redis' host fails
            if "getaddrinfo failed" in str(e).lower() and "localhost" not in self._url:
                logger.warning(f"Failed to connect to {self._url}, trying localhost...")
                try:
                    self._url = "redis://127.0.0.1:6379"
                    self._redis = redis.from_url(self._url, socket_timeout=5.0)
                    await self._redis.ping()
                    self._initialized = True
                    logger.info("Connected to Redis via localhost fallback")
                    return
                except Exception:
                    pass

            logger.error(f"Failed to connect to Redis: {e}")
            self._redis = None

    async def close(self) -> None:
        if self._redis:
            await self._redis.aclose()

    async def get(self, key: str) -> Optional[str]:
        if not self._redis:
            return None
        return await self._redis.get(key)

    async def set(self, key: str, value: str, expire: int = None) -> bool:
        if not self._redis:
            return False
        return await self._redis.set(key, value, ex=expire)

    async def health_check(self) -> bool:
        if not self._redis:
            return False
        try:
            return await self._redis.ping()
        except Exception:
            return False

    # --- Working Memory (WorkingMemory Model) ---

    async def push_message(self, session_id: str, message: dict) -> None:
        """Push a message to the recent chat history list."""
        if not self._redis:
            return
        key = f"wm:history:{session_id}"
        import json

        await self._redis.lpush(key, json.dumps(message))
        # Keep only the last 20 messages for working memory
        await self._redis.ltrim(key, 0, 19)

    async def get_messages(self, session_id: str, limit: int = 10) -> list:
        """Get the most recent messages from history."""
        if not self._redis:
            return []
        key = f"wm:history:{session_id}"
        raw_msgs = await self._redis.lrange(key, 0, limit - 1)
        import json

        # Redis return bytes, decode and parse
        return [json.loads(m.decode("utf-8")) for m in reversed(raw_msgs)]

    async def set_focus(self, agent_id: str, focus: str) -> None:
        """Update the agent's current focus/intent."""
        if not self._redis:
            return
        key = f"wm:focus:{agent_id}"
        await self._redis.set(key, focus)

    async def get_focus(self, agent_id: str) -> Optional[str]:
        """Retrieve the agent's current focus/intent."""
        if not self._redis:
            return None
        key = f"wm:focus:{agent_id}"
        val = await self._redis.get(key)
        return val.decode("utf-8") if val else None


_cache_client: Optional[CacheClient] = None


def get_cache() -> CacheClient:
    global _cache_client
    if _cache_client is None:
        _cache_client = CacheClient()
    return _cache_client
