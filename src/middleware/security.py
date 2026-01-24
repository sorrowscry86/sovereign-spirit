"""
VoidCat RDC: Security Middleware
================================
Implements protective wards for the Sovereign Spirit API.

Features:
- API Key authentication (optional, enabled via environment)
- Rate limiting per client IP
- Request sanitization utilities
"""

import os
import re
import time
import logging
from typing import Dict, Optional, Callable
from collections import defaultdict

from fastapi import Request, HTTPException, Security
from fastapi.security import APIKeyHeader

logger = logging.getLogger("sovereign.security")

# =============================================================================
# Configuration
# =============================================================================

# API Key authentication (disabled by default for development)
API_KEY_ENABLED = os.getenv("SOVEREIGN_API_KEY_ENABLED", "false").lower() == "true"
API_KEY = os.getenv("SOVEREIGN_API_KEY", "")

# Rate limiting configuration
RATE_LIMIT_ENABLED = os.getenv("SOVEREIGN_RATE_LIMIT_ENABLED", "true").lower() == "true"
RATE_LIMIT_REQUESTS = int(os.getenv("SOVEREIGN_RATE_LIMIT_REQUESTS", "60"))  # requests per window
RATE_LIMIT_WINDOW = int(os.getenv("SOVEREIGN_RATE_LIMIT_WINDOW", "60"))  # window in seconds

# Exempt paths from authentication (health checks, docs)
AUTH_EXEMPT_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}

# =============================================================================
# API Key Authentication
# =============================================================================

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    request: Request,
    api_key: Optional[str] = Security(api_key_header)
) -> Optional[str]:
    """
    Verify the API key if authentication is enabled.

    Returns the API key if valid, raises HTTPException if invalid.
    Allows unauthenticated access if API_KEY_ENABLED is False.
    """
    # Skip auth for exempt paths
    if request.url.path in AUTH_EXEMPT_PATHS:
        return None

    # Skip auth for WebSocket upgrade requests
    if request.url.path == "/ws":
        return None

    # If API key auth is disabled, allow all requests
    if not API_KEY_ENABLED:
        return None

    # If enabled but no key configured, log warning and allow
    if not API_KEY:
        logger.warning("API key authentication enabled but no key configured!")
        return None

    # Verify the provided key
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required. Provide X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if api_key != API_KEY:
        logger.warning(f"Invalid API key attempt from {get_client_ip(request)}")
        raise HTTPException(
            status_code=403,
            detail="Invalid API key.",
        )

    return api_key


# =============================================================================
# Rate Limiting
# =============================================================================

class RateLimiter:
    """
    Simple in-memory rate limiter using sliding window algorithm.

    For production, consider using Redis-based rate limiting.
    """

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, list] = defaultdict(list)

    def is_allowed(self, client_id: str) -> bool:
        """
        Check if a request from client_id is allowed.

        Returns True if allowed, False if rate limited.
        """
        now = time.time()
        window_start = now - self.window_seconds

        # Clean old entries and get recent requests
        self._requests[client_id] = [
            ts for ts in self._requests[client_id] if ts > window_start
        ]

        if len(self._requests[client_id]) >= self.max_requests:
            return False

        self._requests[client_id].append(now)
        return True

    def get_remaining(self, client_id: str) -> int:
        """Get remaining requests for this client."""
        now = time.time()
        window_start = now - self.window_seconds
        recent = [ts for ts in self._requests[client_id] if ts > window_start]
        return max(0, self.max_requests - len(recent))

    def cleanup(self):
        """Remove stale entries to prevent memory growth."""
        now = time.time()
        window_start = now - self.window_seconds

        stale_keys = []
        for client_id, timestamps in self._requests.items():
            self._requests[client_id] = [ts for ts in timestamps if ts > window_start]
            if not self._requests[client_id]:
                stale_keys.append(client_id)

        for key in stale_keys:
            del self._requests[key]


# Global rate limiter instance
_rate_limiter = RateLimiter(RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW)


def get_client_ip(request: Request) -> str:
    """Extract client IP from request, handling proxies."""
    # Check for forwarded header (behind reverse proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    # Check for real IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Fall back to direct client
    if request.client:
        return request.client.host

    return "unknown"


async def check_rate_limit(request: Request) -> None:
    """
    Check if request is within rate limits.

    Raises HTTPException 429 if rate limited.
    """
    if not RATE_LIMIT_ENABLED:
        return

    # Skip rate limiting for exempt paths
    if request.url.path in AUTH_EXEMPT_PATHS:
        return

    client_ip = get_client_ip(request)

    if not _rate_limiter.is_allowed(client_ip):
        remaining = _rate_limiter.get_remaining(client_ip)
        logger.warning(f"Rate limit exceeded for {client_ip}")
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please slow down.",
            headers={
                "Retry-After": str(RATE_LIMIT_WINDOW),
                "X-RateLimit-Limit": str(RATE_LIMIT_REQUESTS),
                "X-RateLimit-Remaining": str(remaining),
            }
        )


# =============================================================================
# Input Sanitization
# =============================================================================

# Patterns for potentially dangerous content
SCRIPT_PATTERN = re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL)
HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
SQL_INJECTION_PATTERN = re.compile(
    r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER|CREATE|TRUNCATE)\b)",
    re.IGNORECASE
)


def sanitize_message_content(content: str) -> str:
    """
    Sanitize user message content to prevent XSS and injection attacks.

    - Removes script tags
    - Escapes HTML entities
    - Logs potential SQL injection attempts (doesn't block, as it might be legitimate)

    Returns sanitized content.
    """
    if not content:
        return content

    # Remove script tags entirely
    sanitized = SCRIPT_PATTERN.sub("[script removed]", content)

    # Remove other HTML tags but keep content
    sanitized = HTML_TAG_PATTERN.sub("", sanitized)

    # Log potential SQL injection (don't block - could be legitimate discussion)
    if SQL_INJECTION_PATTERN.search(content):
        logger.info(f"Potential SQL keywords in message (length={len(content)})")

    return sanitized.strip()


def sanitize_agent_name(name: str) -> str:
    """
    Sanitize agent name to prevent path traversal and injection.

    Removes any characters that aren't alphanumeric, underscore, or hyphen.
    """
    if not name:
        return name

    # Only allow safe characters
    return re.sub(r"[^a-zA-Z0-9_-]", "", name)[:50]
