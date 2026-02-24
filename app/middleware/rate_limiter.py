"""
Rate limiting middleware using in-memory sliding window algorithm.

Architecture Decision:
- In-memory implementation suitable for single-process / development
- For multi-process production: replace with Redis-backed implementation
  (see RedisRateLimiter stub at bottom of file)
- Sliding window algorithm is more accurate than fixed window
- Per-IP limiting (not per-user) to handle unauthenticated endpoints
"""

import asyncio
import time
from collections import defaultdict, deque
from typing import Deque, Dict

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings
from app.core.exceptions import RateLimitError

logger = structlog.get_logger(__name__)

# Endpoints with custom limits
ENDPOINT_LIMITS = {
    "/api/v1/chat/query": (
        settings.RATE_LIMIT_CHAT_REQUESTS,
        settings.RATE_LIMIT_CHAT_WINDOW_SECONDS,
    ),
}

# Default limits
DEFAULT_LIMIT = settings.RATE_LIMIT_REQUESTS
DEFAULT_WINDOW = settings.RATE_LIMIT_WINDOW_SECONDS

# Endpoints exempt from rate limiting (health checks, docs)
EXEMPT_PATHS = {"/health", "/api/docs", "/api/openapi.json", "/api/redoc"}


class SlidingWindowRateLimiter:
    """
    Thread-safe sliding window rate limiter using asyncio.Lock.

    Data structure: {identifier: deque of timestamps}
    Sliding window: count requests in the last `window_seconds`
    """

    def __init__(self):
        self._requests: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def is_allowed(self, identifier: str, limit: int, window: int) -> tuple[bool, int]:
        """
        Check if request is allowed.
        Returns (allowed: bool, remaining: int)
        """
        now = time.time()
        window_start = now - window

        async with self._lock:
            timestamps = self._requests[identifier]

            # Remove expired timestamps (sliding window)
            while timestamps and timestamps[0] < window_start:
                timestamps.popleft()

            count = len(timestamps)

            if count >= limit:
                return False, 0

            timestamps.append(now)
            return True, limit - count - 1

    async def cleanup_expired(self) -> None:
        """
        Periodic cleanup of expired entries to prevent memory growth.
        Call this from a background task every few minutes.
        """
        async with self._lock:
            cutoff = time.time() - max(DEFAULT_WINDOW, settings.RATE_LIMIT_CHAT_WINDOW_SECONDS)
            to_delete = []
            for key, timestamps in self._requests.items():
                while timestamps and timestamps[0] < cutoff:
                    timestamps.popleft()
                if not timestamps:
                    to_delete.append(key)
            for key in to_delete:
                del self._requests[key]


# Module-level limiter instance
_limiter = SlidingWindowRateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware that checks per-IP limits for each request.
    Sets X-RateLimit-Remaining header on all responses.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path

        # Skip exempt paths
        if path in EXEMPT_PATHS or path.startswith("/api/docs"):
            return await call_next(request)

        # Determine limit for this endpoint
        limit, window = ENDPOINT_LIMITS.get(path, (DEFAULT_LIMIT, DEFAULT_WINDOW))

        # Use real IP (handle proxy headers)
        client_ip = self._get_client_ip(request)
        identifier = f"{client_ip}:{path}"

        allowed, remaining = await _limiter.is_allowed(identifier, limit, window)

        if not allowed:
            logger.warning(
                "Rate limit exceeded",
                ip=client_ip,
                path=path,
            )
            return Response(
                content='{"error":"RATE_LIMIT","message":"Rate limit exceeded","details":{"retry_after":60}}',
                status_code=429,
                headers={
                    "Content-Type": "application/json",
                    "Retry-After": str(window),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Window": str(window),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        """Extract real client IP, handling reverse proxy headers."""
        # Check X-Forwarded-For (set by nginx/load balancer)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first (original client) IP
            return forwarded_for.split(",")[0].strip()

        # X-Real-IP (nginx)
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        # Fall back to direct connection
        if request.client:
            return request.client.host
        return "unknown"


# ── Redis-backed Rate Limiter (Production Multi-Process) ──────────────────────
# Uncomment and configure for multi-worker deployments:
#
# import redis.asyncio as redis
#
# class RedisRateLimiter:
#     """
#     Redis-backed rate limiter using sorted sets.
#     Safe across multiple processes/workers.
#     """
#     def __init__(self, redis_url: str):
#         self.redis = redis.from_url(redis_url)
#
#     async def is_allowed(self, identifier: str, limit: int, window: int) -> tuple[bool, int]:
#         now = time.time()
#         window_start = now - window
#         key = f"rl:{identifier}"
#
#         async with self.redis.pipeline(transaction=True) as pipe:
#             pipe.zremrangebyscore(key, 0, window_start)
#             pipe.zcard(key)
#             pipe.zadd(key, {str(now): now})
#             pipe.expire(key, window)
#             results = await pipe.execute()
#
#         count = results[1]
#         if count >= limit:
#             await self.redis.zrem(key, str(now))
#             return False, 0
#         return True, limit - count - 1
